"""Generate counterfactual scenarios and recommendation narratives."""

from __future__ import annotations

from dualexis.orchestration.models import OrchestrationRecommendation, SeverityLevel
from dualexis.simulation.scenario import ScenarioId
from dualexis.sssg.evidence import infer_safety_state_from_evidence
from dualexis.sssg.models import EvidenceRecord, SafetyState, StateTransition, StateTransitionTrace
from dualexis.counterfactual.interventions import (
    STANDARD_INTERVENTIONS,
    apply_intervention,
    perturbed_metric_snapshot,
)
from dualexis.counterfactual.models import (
    CounterfactualInterventionKind,
    CounterfactualRecommendation,
    CounterfactualScenario,
)

_STATE_SEVERITY: dict[SafetyState, int] = {
    SafetyState.NORMAL: 0,
    SafetyState.CROWDING_RISK: 1,
    SafetyState.AUDIO_STRESS: 1,
    SafetyState.MULTI_MODAL_CONFLICT: 2,
    SafetyState.EXIT_IMPAIRMENT: 2,
    SafetyState.EVACUATION_CANDIDATE: 3,
}

_ACTION_BY_STATE: dict[SafetyState, str] = {
    SafetyState.NORMAL: "monitor",
    SafetyState.CROWDING_RISK: "notify_staff",
    SafetyState.AUDIO_STRESS: "notify_staff",
    SafetyState.MULTI_MODAL_CONFLICT: "request_review",
    SafetyState.EXIT_IMPAIRMENT: "notify_staff",
    SafetyState.EVACUATION_CANDIDATE: "escalate",
}

_HIGH_ACTIONS = frozenset({"escalate", "request_review", "notify_staff"})


def _state_phrase(state: SafetyState) -> str:
    return state.value.replace("_", " ")


def action_for_state(state: SafetyState) -> str:
    return _ACTION_BY_STATE.get(state, "monitor")


def _latest_transition_for_zone(
    trace: StateTransitionTrace,
    zone_id: str,
) -> StateTransition | None:
    zone_transitions = [t for t in trace.transitions if t.zone_id == zone_id]
    if not zone_transitions:
        return None
    return max(zone_transitions, key=lambda item: item.tick)


def _evidence_for_recommendation(
    trace: StateTransitionTrace,
    recommendation: OrchestrationRecommendation,
) -> tuple[EvidenceRecord, ...]:
    transition = _latest_transition_for_zone(trace, recommendation.target_zone_id)
    if transition is not None and transition.evidence:
        return transition.evidence
    for transition in reversed(trace.transitions):
        if transition.zone_id == recommendation.target_zone_id:
            return transition.evidence
    return ()


def simulate_counterfactual_scenario(
    evidence: tuple[EvidenceRecord, ...],
    *,
    intervention: CounterfactualInterventionKind,
    zone_id: str,
    scenario_id: str,
    spec_id: str,
) -> CounterfactualScenario:
    from dualexis.counterfactual.interventions import STANDARD_INTERVENTIONS

    spec = next(s for s in STANDARD_INTERVENTIONS if s.kind == intervention)
    perturbed = apply_intervention(evidence, intervention, zone_id=zone_id)
    try:
        scenario_enum = ScenarioId(scenario_id)
    except ValueError:
        scenario_enum = None

    cf_state = infer_safety_state_from_evidence(
        perturbed,
        scenario_id=scenario_enum,
        zone_id=zone_id,
    )
    cf_action = action_for_state(cf_state)
    metrics = perturbed_metric_snapshot(perturbed, intervention, zone_id=zone_id)

    explanation = (
        f"Under the counterfactual that {spec.hypothesis}, inferred safety state would be "
        f"{_state_phrase(cf_state)} with advisory action '{cf_action}'. "
    )
    if cf_state == SafetyState.NORMAL:
        explanation += "Staff escalation would likely not be required."
    elif cf_action == "monitor":
        explanation += "The system would remain in routine monitoring."
    else:
        explanation += "Some advisory action may still apply, but severity is reduced."

    baseline_action = action_for_state(
        infer_safety_state_from_evidence(evidence, scenario_id=scenario_enum, zone_id=zone_id)
    )
    would_avoid = (
        baseline_action in _HIGH_ACTIONS
        and cf_action in {"monitor", "no_action"}
    ) or _STATE_SEVERITY.get(cf_state, 0) < _STATE_SEVERITY.get(
        infer_safety_state_from_evidence(evidence, scenario_id=scenario_enum, zone_id=zone_id),
        0,
    )

    return CounterfactualScenario(
        scenario_id=spec_id,
        intervention=intervention,
        hypothesis=spec.hypothesis,
        question=spec.question,
        perturbed_metrics=metrics,
        counterfactual_state=cf_state,
        counterfactual_action=cf_action,
        would_avoid_recommendation=would_avoid,
        explanation=explanation,
        confidence=0.72 if would_avoid else 0.58,
    )


def build_counterfactual_recommendation(
    recommendation: OrchestrationRecommendation,
    trace: StateTransitionTrace,
    *,
    scenario_id: str,
    seed: int,
) -> CounterfactualRecommendation | None:
    """Attach standard what-if scenarios to one pipeline recommendation."""
    evidence = _evidence_for_recommendation(trace, recommendation)
    if not evidence:
        return None

    transition = _latest_transition_for_zone(trace, recommendation.target_zone_id)
    tick = transition.tick if transition else 0
    baseline_state = (
        transition.to_state
        if transition
        else trace.final_states.get(recommendation.target_zone_id, SafetyState.NORMAL)
    )

    counterfactuals: list[CounterfactualScenario] = []
    for index, spec in enumerate(STANDARD_INTERVENTIONS):
        counterfactuals.append(
            simulate_counterfactual_scenario(
                evidence,
                intervention=spec.kind,
                zone_id=recommendation.target_zone_id,
                scenario_id=scenario_id,
                spec_id=f"cf-{recommendation.recommendation_id.hex[:8]}-{index}",
            )
        )

    lines = [
        f"What-if analysis for recommendation in zone {recommendation.target_zone_id} "
        f"(baseline: {_state_phrase(baseline_state)}, action '{recommendation.action}'):"
    ]
    for cf in counterfactuals:
        lines.append(f"  • {cf.question}")
        lines.append(f"    → {cf.explanation}")

    return CounterfactualRecommendation(
        recommendation_id=recommendation.recommendation_id,
        scenario_id=scenario_id,
        seed=seed,
        zone_id=recommendation.target_zone_id,
        tick=tick,
        baseline_state=baseline_state,
        baseline_action=recommendation.action,
        baseline_severity=recommendation.severity,
        baseline_rationale=recommendation.rationale,
        counterfactuals=tuple(counterfactuals),
        summary="\n".join(lines),
    )


def synthesize_recommendation_from_trace(
    trace: StateTransitionTrace,
    *,
    zone_id: str,
) -> OrchestrationRecommendation | None:
    """Build a synthetic recommendation when the pipeline emits none (low-severity runs)."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from dualexis.orchestration.models import HumanReviewStatus

    transition = _latest_transition_for_zone(trace, zone_id)
    if transition is None:
        state = trace.final_states.get(zone_id, SafetyState.NORMAL)
        if state == SafetyState.NORMAL:
            return None
        tick = 0
        rationale = f"Zone {zone_id} in {_state_phrase(state)}."
    else:
        state = transition.to_state
        tick = transition.tick
        rationale = transition.explanation

    action = action_for_state(state)
    severity = SeverityLevel.HIGH if action in {"escalate", "request_review"} else SeverityLevel.MEDIUM
    if state == SafetyState.NORMAL:
        return None

    return OrchestrationRecommendation(
        recommendation_id=uuid4(),
        based_on_events=[uuid4()],
        target_zone_id=zone_id,
        action=action,
        rationale=rationale,
        severity=severity,
        requires_human_review=severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL},
        human_review_status=HumanReviewStatus.PENDING,
        created_at=datetime.now(tz=UTC),
    )


__all__ = [
    "action_for_state",
    "build_counterfactual_recommendation",
    "simulate_counterfactual_scenario",
    "synthesize_recommendation_from_trace",
]
