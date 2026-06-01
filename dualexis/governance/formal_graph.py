"""Formal three-phase governance graph (Graphviz)."""

from __future__ import annotations

from dualexis.governance.formal_models import (
    GovernanceGraphEdge,
    GovernanceMacroState,
)


def build_formal_governance_graph_dot(
    edges: tuple[GovernanceGraphEdge, ...] | list[GovernanceGraphEdge] = (),
) -> str:
    ai = GovernanceMacroState.AI_RECOMMENDATION.value
    human = GovernanceMacroState.HUMAN_REVIEW.value
    inst = GovernanceMacroState.INSTITUTIONAL_ESCALATION.value

    lines = [
        "digraph FormalHumanAIGovernance {",
        '  rankdir=LR;',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica"];',
        f'  {ai} [label="s^{{AI}}\\nAI recommendation", fillcolor="#fff3cd"];',
        f'  {human} [label="s^{{H}}\\nHuman review", fillcolor="#fdebd0"];',
        f'  {inst} [label="s^{{I}}\\nInstitutional escalation", fillcolor="#cce5ff"];',
    ]

    if edges:
        for edge in edges:
            label = f"{edge.symbol.value} (p={edge.probability:.2f})"
            lines.append(
                f'  {edge.from_state.value} -> {edge.to_state.value} '
                f'[label="{label}"];'
            )
    else:
        lines.extend(
            [
                f'  {ai} -> {human} [label="τ_issue"];',
                f'  {human} -> {human} [label="accept|override|dismiss"];',
                f'  {human} -> {inst} [label="escalate"];',
                f'  {inst} -> {inst} [label="τ_close"];',
            ]
        )

    lines.append("}")
    return "\n".join(lines)


__all__ = ["build_formal_governance_graph_dot"]
