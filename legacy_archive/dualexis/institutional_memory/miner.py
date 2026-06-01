"""GovernancePatternMiner — extract recurring governance patterns from traces."""

from __future__ import annotations

from collections import Counter, defaultdict

from dualexis.governance.formal_models import GovernanceDecisionTrace, GovernanceTransitionSymbol
from dualexis.institutional_memory.models import GovernancePattern


class GovernancePatternMiner:
    """Mine historical governance patterns from decision traces."""

    def __init__(self, *, min_support: int = 2) -> None:
        self._min_support = min_support

    def mine(self, traces: list[GovernanceDecisionTrace]) -> list[GovernancePattern]:
        if not traces:
            return []

        keyed: Counter[tuple[str, str, str, str, tuple[str, ...], str]] = Counter()
        compliance: dict[tuple[str, str, str, str, tuple[str, ...], str], list[bool]] = (
            defaultdict(list)
        )
        case_meta: dict[tuple[str, str, str, str, tuple[str, ...], str], tuple[str, str, str]] = {}

        for trace in traces:
            severity = _severity_from_trace(trace)
            symbols = tuple(step.symbol.value for step in trace.steps)
            key = (
                trace.scenario_id,
                severity,
                _ai_action(trace),
                trace.terminal_macro_state.value,
                symbols,
                trace.profile.value,
            )
            keyed[key] += 1
            compliance[key].append(trace.policy_compliant)
            case_meta[key] = (trace.scenario_id, severity, _ai_action(trace), trace.profile.value)

        patterns: list[GovernancePattern] = []
        total = len(traces)
        for index, (key, count) in enumerate(keyed.most_common()):
            if count < self._min_support and total > self._min_support:
                continue
            scenario_id, severity, ai_action, terminal, symbols, _profile = key
            compliant = compliance[key]
            patterns.append(
                GovernancePattern(
                    pattern_id=f"gov-{index:04d}",
                    scenario_id=scenario_id,
                    severity=severity,
                    ai_action=ai_action,
                    symbol_sequence=symbols,
                    terminal_state=terminal,
                    support_count=count,
                    support_ratio=round(count / total, 4),
                    policy_compliance_rate=round(sum(compliant) / len(compliant), 4),
                )
            )
        return patterns


def _severity_from_trace(trace: GovernanceDecisionTrace) -> str:
    for step in trace.steps:
        if "severity" in step.metadata:
            return str(step.metadata["severity"])
    return "unknown"


def _ai_action(trace: GovernanceDecisionTrace) -> str:
    for step in trace.steps:
        if "ai_action" in step.metadata:
            return str(step.metadata["ai_action"])
    return "unknown"


def _symbol_sequence(trace: GovernanceDecisionTrace) -> tuple[str, ...]:
    return tuple(step.symbol.value for step in trace.steps)


def extract_escalation_chains(
    traces: list[GovernanceDecisionTrace],
    *,
    min_support: int = 2,
) -> list[tuple[tuple[str, ...], int, tuple[str, ...]]]:
    """Return (chain, count, scenarios) for recurrent escalation paths."""
    chains: Counter[tuple[str, ...]] = Counter()
    scenarios_by_chain: dict[tuple[str, ...], set[str]] = defaultdict(set)

    for trace in traces:
        symbols = [step.symbol.value for step in trace.steps]
        if GovernanceTransitionSymbol.ESCALATE.value not in symbols:
            continue
        start = symbols.index(GovernanceTransitionSymbol.ISSUE.value)
        chain = tuple(symbols[start:])
        chains[chain] += 1
        scenarios_by_chain[chain].add(trace.scenario_id)

    total = sum(chains.values()) or 1
    results: list[tuple[tuple[str, ...], int, tuple[str, ...]]] = []
    for chain, count in chains.most_common():
        if count < min_support and len(traces) > min_support:
            continue
        results.append((chain, count, tuple(sorted(scenarios_by_chain[chain]))))
    return results


__all__ = ["GovernancePatternMiner", "extract_escalation_chains"]
