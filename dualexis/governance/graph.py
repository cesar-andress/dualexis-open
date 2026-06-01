"""Governance state machine graph (Graphviz DOT)."""

from __future__ import annotations

from dualexis.governance.models import GovernanceState, OperatorAction


def build_governance_graph_dot() -> str:
    """Emit the formal Human-AI governance state transition graph."""
    pending = GovernanceState.PENDING_REVIEW.value
    lines = [
        "digraph HumanAIGovernance {",
        '  rankdir=LR;',
        '  node [shape=box, style=rounded, fontname="Helvetica"];',
        f'  {pending} [label="PENDING_REVIEW\\n(AI recommendation)", fillcolor="#fff3cd", style="rounded,filled"];',
        f'  {GovernanceState.REVIEWED.value} [label="REVIEWED\\n(accept)", fillcolor="#d4edda", style="rounded,filled"];',
        f'  {GovernanceState.OVERRIDDEN.value} [label="OVERRIDDEN", fillcolor="#f8d7da", style="rounded,filled"];',
        f'  {GovernanceState.ESCALATED.value} [label="ESCALATED", fillcolor="#cce5ff", style="rounded,filled"];',
        f'  {GovernanceState.DISMISSED.value} [label="DISMISSED", fillcolor="#e2e3e5", style="rounded,filled"];',
        '  ai_copilot [label="AI Copilot\\n(L4–L5 advisory)", shape=ellipse, style=dashed];',
        '  operator [label="Human operator", shape=ellipse, fillcolor="#fdebd0", style="filled"];',
        "  ai_copilot -> operator [label=\"recommendation\"];",
        f"  ai_copilot -> {pending} [label=\"requires_human_review\"];",
        f"  operator -> {pending} [style=dotted, label=\"queue\"];",
    ]
    for action in OperatorAction:
        target = {
            OperatorAction.ACCEPT: GovernanceState.REVIEWED,
            OperatorAction.OVERRIDE: GovernanceState.OVERRIDDEN,
            OperatorAction.ESCALATE: GovernanceState.ESCALATED,
            OperatorAction.DISMISS: GovernanceState.DISMISSED,
        }[action]
        lines.append(
            f"  {pending} -> {target.value} "
            f'[label="{action.value}", color="#333333"];'
        )
    lines.append("}")
    return "\n".join(lines)


__all__ = ["build_governance_graph_dot"]
