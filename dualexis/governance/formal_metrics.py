"""Formal governance audit metrics."""

from __future__ import annotations

from collections import Counter, defaultdict

from dualexis.governance.formal_models import (
    FormalGovernanceMetrics,
    GovernanceDecisionTrace,
    GovernanceGraph,
    GovernanceGraphEdge,
    GovernanceMacroState,
    GovernanceTransitionSymbol,
)
from dualexis.governance.state_machine import TRANSITION_RELATION


def compute_formal_metrics(traces: list[GovernanceDecisionTrace]) -> FormalGovernanceMetrics:
    if not traces:
        return FormalGovernanceMetrics(
            governance_compliance_score=1.0,
            institutional_reliance_index=0.0,
            human_override_resilience=1.0,
            decision_traceability=1.0,
        )

    compliant = sum(1 for trace in traces if trace.policy_compliant)
    governance_compliance_score = compliant / len(traces)

    escalation_required = [t for t in traces if t.requires_escalation]
    if escalation_required:
        escalated_ok = sum(
            1
            for t in escalation_required
            if t.terminal_macro_state == GovernanceMacroState.INSTITUTIONAL_ESCALATION
        )
        institutional_reliance_index = escalated_ok / len(escalation_required)
    else:
        institutional_reliance_index = 1.0

    wrong_ai = [t for t in traces if not t.ai_correct]
    if wrong_ai:
        overrides = sum(
            1
            for t in wrong_ai
            if any(step.symbol == GovernanceTransitionSymbol.OVERRIDE for step in t.steps)
        )
        human_override_resilience = overrides / len(wrong_ai)
    else:
        human_override_resilience = 1.0

    traceable = sum(1 for t in traces if t.trace_complete and len(t.steps) >= 2)
    decision_traceability = traceable / len(traces)

    return FormalGovernanceMetrics(
        governance_compliance_score=round(governance_compliance_score, 4),
        institutional_reliance_index=round(institutional_reliance_index, 4),
        human_override_resilience=round(human_override_resilience, 4),
        decision_traceability=round(decision_traceability, 4),
    )


def build_governance_graph(traces: list[GovernanceDecisionTrace]) -> GovernanceGraph:
    """Build empirical governance graph with edge counts and probabilities."""
    counts: Counter[tuple[str, str, str]] = Counter()
    outgoing: dict[str, int] = defaultdict(int)

    for trace in traces:
        for step in trace.steps:
            key = (step.from_state.value, step.symbol.value, step.to_state.value)
            counts[key] += 1
            outgoing[step.from_state.value] += 1

    edges: list[GovernanceGraphEdge] = []
    for (from_val, symbol_val, to_val), count in sorted(counts.items()):
        from_state = GovernanceMacroState(from_val)
        to_state = GovernanceMacroState(to_val)
        symbol = GovernanceTransitionSymbol(symbol_val)
        prob = count / outgoing[from_val] if outgoing[from_val] else 0.0
        edges.append(
            GovernanceGraphEdge(
                from_state=from_state,
                to_state=to_state,
                symbol=symbol,
                probability=round(prob, 4),
                count=count,
            )
        )

    matrix: dict[str, dict[str, float]] = {}
    for from_state in GovernanceMacroState:
        matrix[from_state.value] = {}
        for symbol in GovernanceTransitionSymbol:
            target = next(
                (
                    transition.to_state
                    for transition in TRANSITION_RELATION
                    if transition.from_state == from_state and transition.symbol == symbol
                ),
                None,
            )
            if target is None:
                continue
            key = (from_state.value, symbol.value, target.value)
            matrix[from_state.value][symbol.value] = round(
                counts[key] / outgoing[from_state.value] if outgoing[from_state.value] else 0.0,
                4,
            )

    from dualexis.governance.formal_graph import build_formal_governance_graph_dot

    return GovernanceGraph(
        nodes=tuple(GovernanceMacroState),
        edges=tuple(edges),
        transition_matrix=matrix,
        transition_relation=TRANSITION_RELATION,
        dot=build_formal_governance_graph_dot(edges),
    )


__all__ = ["build_governance_graph", "compute_formal_metrics"]
