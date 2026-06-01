"""InstitutionalMemoryGraph construction from mined patterns."""

from __future__ import annotations

from collections import Counter, defaultdict

from dualexis.governance.formal_models import GovernanceDecisionTrace
from dualexis.institutional_memory.miner import (
    GovernancePatternMiner,
    extract_escalation_chains,
)
from dualexis.institutional_memory.models import (
    EscalationChainPattern,
    InstitutionalMemoryGraph,
    MemoryEdgeKind,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryNodeKind,
    NearMissPattern,
    OverridePattern,
)
from dualexis.institutional_memory.near_miss import NearMissDetector
from dualexis.governance.formal_models import GovernanceTransitionSymbol


class InstitutionalMemoryGraphBuilder:
    """Build IMG from TSGG governance trace corpus."""

    def __init__(self, *, min_support: int = 2) -> None:
        self._min_support = min_support

    def build(
        self,
        traces: list[GovernanceDecisionTrace],
    ) -> InstitutionalMemoryGraph:
        miner = GovernancePatternMiner(min_support=self._min_support)
        governance_patterns = tuple(miner.mine(traces))
        near_miss_patterns = tuple(NearMissDetector().detect(traces))
        escalation_chains = tuple(self._escalation_patterns(traces))
        override_patterns = tuple(self._override_patterns(traces))

        nodes, edges = self._graph_topology(
            traces,
            governance_patterns,
            near_miss_patterns,
            escalation_chains,
            override_patterns,
        )
        dot = _build_img_dot(nodes, edges)

        return InstitutionalMemoryGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
            governance_patterns=governance_patterns,
            near_miss_patterns=near_miss_patterns,
            escalation_chains=escalation_chains,
            override_patterns=override_patterns,
            trace_count=len(traces),
            dot=dot,
        )

    def _escalation_patterns(
        self,
        traces: list[GovernanceDecisionTrace],
    ) -> list[EscalationChainPattern]:
        total = len(traces) or 1
        raw = extract_escalation_chains(traces, min_support=self._min_support)
        return [
            EscalationChainPattern(
                pattern_id=f"esc-{index:04d}",
                chain=chain,
                occurrence_count=count,
                support_ratio=round(count / total, 4),
                scenarios=scenarios,
            )
            for index, (chain, count, scenarios) in enumerate(raw)
        ]

    def _override_patterns(
        self,
        traces: list[GovernanceDecisionTrace],
    ) -> list[OverridePattern]:
        buckets: Counter[tuple[str, str, str]] = Counter()
        corrected: dict[tuple[str, str, str], int] = defaultdict(int)

        for trace in traces:
            if not any(step.symbol == GovernanceTransitionSymbol.OVERRIDE for step in trace.steps):
                continue
            severity = "unknown"
            ai_action = "unknown"
            for step in trace.steps:
                severity = step.metadata.get("severity", severity)
                ai_action = step.metadata.get("ai_action", ai_action)
            key = (trace.scenario_id, ai_action, severity)
            buckets[key] += 1
            if not trace.ai_correct:
                corrected[key] += 1

        total = sum(buckets.values()) or 1
        patterns: list[OverridePattern] = []
        for index, (key, count) in enumerate(buckets.most_common()):
            scenario_id, ai_action, severity = key
            patterns.append(
                OverridePattern(
                    pattern_id=f"ovr-{index:04d}",
                    scenario_id=scenario_id,
                    ai_action=ai_action,
                    severity=severity,
                    occurrence_count=count,
                    support_ratio=round(count / total, 4),
                    corrected_ai_incorrect=corrected[key],
                )
            )
        return patterns

    def _graph_topology(self, traces, governance_patterns, near_miss, escalation, override):
        nodes: dict[str, MemoryGraphNode] = {}
        edges: list[MemoryGraphEdge] = []

        def add_node(node_id: str, kind: MemoryNodeKind, label: str) -> None:
            if node_id not in nodes:
                nodes[node_id] = MemoryGraphNode(node_id=node_id, kind=kind, label=label)

        transition_counts: Counter[tuple[str, str, str]] = Counter()
        for trace in traces:
            add_node(f"sc:{trace.scenario_id}", MemoryNodeKind.SCENARIO, trace.scenario_id)
            for step in trace.steps:
                from_id = f"st:{step.from_state.value}"
                to_id = f"st:{step.to_state.value}"
                add_node(from_id, MemoryNodeKind.GOVERNANCE_STATE, step.from_state.value)
                add_node(to_id, MemoryNodeKind.GOVERNANCE_STATE, step.to_state.value)
                transition_counts[(from_id, to_id, step.symbol.value)] += 1

        total_trans = sum(transition_counts.values()) or 1
        for (from_id, to_id, symbol), count in transition_counts.items():
            edges.append(
                MemoryGraphEdge(
                    from_id=from_id,
                    to_id=to_id,
                    kind=MemoryEdgeKind.OBSERVED_TRANSITION,
                    weight=round(count / total_trans, 4),
                    count=count,
                )
            )
            add_node(f"act:{symbol}", MemoryNodeKind.OPERATOR_ACTION, symbol)

        for pattern in governance_patterns:
            pid = f"pat:{pattern.pattern_id}"
            add_node(pid, MemoryNodeKind.PATTERN, pattern.pattern_id)
            edges.append(
                MemoryGraphEdge(
                    from_id=f"sc:{pattern.scenario_id}",
                    to_id=pid,
                    kind=MemoryEdgeKind.PATTERN_SUPPORT,
                    weight=pattern.support_ratio,
                    count=pattern.support_count,
                )
            )

        for pattern in near_miss:
            pid = f"nm:{pattern.pattern_id}"
            add_node(pid, MemoryNodeKind.PATTERN, pattern.near_miss_type)
            edges.append(
                MemoryGraphEdge(
                    from_id=f"sc:{pattern.scenario_id}",
                    to_id=pid,
                    kind=MemoryEdgeKind.NEAR_MISS_LINK,
                    weight=pattern.occurrence_count,
                    count=pattern.occurrence_count,
                )
            )

        for chain in escalation:
            pid = f"esc:{chain.pattern_id}"
            add_node(pid, MemoryNodeKind.PATTERN, "escalation_chain")
            edges.append(
                MemoryGraphEdge(
                    from_id="st:human_review",
                    to_id="st:institutional_escalation",
                    kind=MemoryEdgeKind.ESCALATION_CHAIN,
                    weight=chain.support_ratio,
                    count=chain.occurrence_count,
                )
            )

        for pattern in override:
            pid = f"ovr:{pattern.pattern_id}"
            add_node(pid, MemoryNodeKind.PATTERN, "override")
            edges.append(
                MemoryGraphEdge(
                    from_id=f"sc:{pattern.scenario_id}",
                    to_id=pid,
                    kind=MemoryEdgeKind.PATTERN_SUPPORT,
                    weight=pattern.support_ratio,
                    count=pattern.occurrence_count,
                )
            )

        return list(nodes.values()), edges


def _build_img_dot(nodes: list[MemoryGraphNode], edges: list[MemoryGraphEdge]) -> str:
    lines = [
        "digraph InstitutionalMemory {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
        '  edge [fontname="Helvetica", fontsize=9];',
    ]
    colors = {
        MemoryNodeKind.SCENARIO: "#e8f4fd",
        MemoryNodeKind.GOVERNANCE_STATE: "#fff3cd",
        MemoryNodeKind.OPERATOR_ACTION: "#fdebd0",
        MemoryNodeKind.PATTERN: "#fadbd8",
    }
    for node in nodes:
        fill = colors.get(node.kind, "#ffffff")
        lines.append(f'  "{node.node_id}" [label="{node.label}", fillcolor="{fill}"];')
    for edge in edges:
        label = f"{edge.kind.value} n={edge.count}"
        lines.append(
            f'  "{edge.from_id}" -> "{edge.to_id}" '
            f'[label="{label}", penwidth={max(1.0, edge.weight * 4):.1f}];'
        )
    lines.append("}")
    return "\n".join(lines)


__all__ = ["InstitutionalMemoryGraphBuilder"]
