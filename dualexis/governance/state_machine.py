"""Mathematical governance state machine δ: S × Σ → S."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from dualexis.governance.formal_models import (
    GovernanceDecisionTrace,
    GovernanceMacroState,
    GovernanceTraceStep,
    GovernanceTransitionDef,
    GovernanceTransitionSymbol,
)
from dualexis.governance.models import (
    GovernanceReviewCase,
    GovernanceState,
    OperatorAction,
    OperatorDecision,
)

# Transition relation T ⊆ S × Σ × S (documented guards).
TRANSITION_RELATION: tuple[GovernanceTransitionDef, ...] = (
    GovernanceTransitionDef(
        from_state=GovernanceMacroState.AI_RECOMMENDATION,
        symbol=GovernanceTransitionSymbol.ISSUE,
        to_state=GovernanceMacroState.HUMAN_REVIEW,
        guard="requires_human_review(s)",
    ),
    GovernanceTransitionDef(
        from_state=GovernanceMacroState.HUMAN_REVIEW,
        symbol=GovernanceTransitionSymbol.ACCEPT,
        to_state=GovernanceMacroState.HUMAN_REVIEW,
        guard="operator_accept(u)",
    ),
    GovernanceTransitionDef(
        from_state=GovernanceMacroState.HUMAN_REVIEW,
        symbol=GovernanceTransitionSymbol.OVERRIDE,
        to_state=GovernanceMacroState.HUMAN_REVIEW,
        guard="operator_override(u)",
    ),
    GovernanceTransitionDef(
        from_state=GovernanceMacroState.HUMAN_REVIEW,
        symbol=GovernanceTransitionSymbol.DISMISS,
        to_state=GovernanceMacroState.HUMAN_REVIEW,
        guard="operator_dismiss(u)",
    ),
    GovernanceTransitionDef(
        from_state=GovernanceMacroState.HUMAN_REVIEW,
        symbol=GovernanceTransitionSymbol.ESCALATE,
        to_state=GovernanceMacroState.INSTITUTIONAL_ESCALATION,
        guard="policy_escalation_required(s)",
    ),
    GovernanceTransitionDef(
        from_state=GovernanceMacroState.INSTITUTIONAL_ESCALATION,
        symbol=GovernanceTransitionSymbol.CLOSE,
        to_state=GovernanceMacroState.INSTITUTIONAL_ESCALATION,
        guard="institutional_ack(s)",
    ),
)

INITIAL_STATE = GovernanceMacroState.AI_RECOMMENDATION


def delta(
    state: GovernanceMacroState,
    symbol: GovernanceTransitionSymbol,
) -> GovernanceMacroState | None:
    """
    Deterministic transition function δ(s, σ) → s'.

    Returns None if (s, σ) ∉ dom(δ).
    """
    for transition in TRANSITION_RELATION:
        if transition.from_state == state and transition.symbol == symbol:
            return transition.to_state
    return None


def _action_to_symbol(action: OperatorAction) -> GovernanceTransitionSymbol:
    return GovernanceTransitionSymbol(action.value)


def build_decision_trace(
    case: GovernanceReviewCase,
    decision: OperatorDecision,
) -> GovernanceDecisionTrace:
    """Construct auditable macro trace from simulation artefacts."""
    t0 = case.created_at
    t1 = decision.decided_at
    steps: list[GovernanceTraceStep] = [
        GovernanceTraceStep(
            step_index=0,
            from_state=GovernanceMacroState.AI_RECOMMENDATION,
            symbol=GovernanceTransitionSymbol.ISSUE,
            to_state=GovernanceMacroState.HUMAN_REVIEW,
            timestamp=t0,
            micro_state=GovernanceState.PENDING_REVIEW,
            metadata={"ai_action": case.ai_action, "severity": case.severity.value},
        ),
        GovernanceTraceStep(
            step_index=1,
            from_state=GovernanceMacroState.HUMAN_REVIEW,
            symbol=_action_to_symbol(decision.action),
            to_state=delta(GovernanceMacroState.HUMAN_REVIEW, _action_to_symbol(decision.action))
            or GovernanceMacroState.HUMAN_REVIEW,
            timestamp=t1,
            micro_state=decision.resulting_state,
            metadata={"profile": decision.profile.value},
        ),
    ]

    terminal = steps[-1].to_state
    if terminal == GovernanceMacroState.INSTITUTIONAL_ESCALATION:
        steps.append(
            GovernanceTraceStep(
                step_index=2,
                from_state=GovernanceMacroState.INSTITUTIONAL_ESCALATION,
                symbol=GovernanceTransitionSymbol.CLOSE,
                to_state=GovernanceMacroState.INSTITUTIONAL_ESCALATION,
                timestamp=t1 + timedelta(seconds=1),
                micro_state=GovernanceState.ESCALATED,
                metadata={"institutional": "recorded"},
            )
        )

    policy_compliant = _policy_compliant(case, decision, terminal)
    trace_complete = len(steps) >= 2 and steps[0].symbol == GovernanceTransitionSymbol.ISSUE

    return GovernanceDecisionTrace(
        case_id=case.case_id,
        scenario_id=case.scenario_id,
        zone_id=case.zone_id,
        profile=decision.profile,
        steps=tuple(steps),
        terminal_macro_state=terminal,
        ai_correct=case.ai_correct,
        requires_escalation=case.requires_escalation,
        policy_compliant=policy_compliant,
        trace_complete=trace_complete,
    )


def _policy_compliant(
    case: GovernanceReviewCase,
    decision: OperatorDecision,
    terminal: GovernanceMacroState,
) -> bool:
    if case.requires_escalation:
        return terminal == GovernanceMacroState.INSTITUTIONAL_ESCALATION
    if decision.action == OperatorAction.ACCEPT and not case.ai_correct:
        return False
    if decision.action == OperatorAction.OVERRIDE and case.ai_correct:
        return True
    return terminal != GovernanceMacroState.INSTITUTIONAL_ESCALATION or case.requires_escalation


def transition_matrix_latex() -> str:
    """LaTeX align* fragment for δ."""
    lines = ["\\begin{align*}"]
    for index, transition in enumerate(TRANSITION_RELATION):
        suffix = " \\\\" if index < len(TRANSITION_RELATION) - 1 else ""
        lines.append(
            f"  \\delta(\\mathit{{{transition.from_state.value}}}, \\mathit{{{transition.symbol.value}}}) "
            f"&= \\mathit{{{transition.to_state.value}}}{suffix}"
        )
    lines.append("\\end{align*}")
    return "\n".join(lines)


__all__ = [
    "INITIAL_STATE",
    "TRANSITION_RELATION",
    "build_decision_trace",
    "delta",
    "transition_matrix_latex",
]
