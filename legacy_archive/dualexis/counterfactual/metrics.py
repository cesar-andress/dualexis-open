"""Counterfactual evaluation metrics."""

from __future__ import annotations

from dualexis.counterfactual.models import (
    CounterfactualRecommendation,
    CounterfactualTrace,
)
from dualexis.sssg.models import SafetyState

_STATE_SEVERITY: dict[SafetyState, int] = {
    SafetyState.NORMAL: 0,
    SafetyState.CROWDING_RISK: 1,
    SafetyState.AUDIO_STRESS: 1,
    SafetyState.MULTI_MODAL_CONFLICT: 2,
    SafetyState.EXIT_IMPAIRMENT: 2,
    SafetyState.EVACUATION_CANDIDATE: 3,
}


def counterfactual_consistency_for_recommendation(
    recommendation: CounterfactualRecommendation,
) -> float:
    """
    Fraction of counterfactuals where the intervention yields a safer or equal state
    than the baseline (ordinal severity).
    """
    if not recommendation.counterfactuals:
        return 0.0
    base_level = _STATE_SEVERITY.get(recommendation.baseline_state, 0)
    consistent = 0
    for cf in recommendation.counterfactuals:
        cf_level = _STATE_SEVERITY.get(cf.counterfactual_state, 0)
        if cf_level <= base_level or cf.would_avoid_recommendation:
            consistent += 1
    return consistent / len(recommendation.counterfactuals)


def counterfactual_explanation_coverage(
    recommendation: CounterfactualRecommendation,
    *,
    required_interventions: int = 3,
) -> float:
    """1.0 if all standard counterfactuals have non-empty question and explanation."""
    if len(recommendation.counterfactuals) < required_interventions:
        return len(recommendation.counterfactuals) / required_interventions
    complete = sum(
        1
        for cf in recommendation.counterfactuals
        if cf.question.strip() and cf.explanation.strip() and cf.hypothesis.strip()
    )
    return complete / required_interventions


def aggregate_trace_metrics(
    recommendations: list[CounterfactualRecommendation],
) -> tuple[float, float, float]:
    if not recommendations:
        return 1.0, 1.0, 0.0
    consistency = sum(
        counterfactual_consistency_for_recommendation(r) for r in recommendations
    ) / len(recommendations)
    coverage = sum(
        counterfactual_explanation_coverage(r) for r in recommendations
    ) / len(recommendations)
    return consistency, 1.0, coverage


def counterfactual_stability_across_traces(
    traces: list[CounterfactualTrace],
) -> float:
    """Jaccard stability of (intervention, counterfactual_state) signatures across seeds."""
    if len(traces) < 2:
        return 1.0

    def signature(trace: CounterfactualTrace) -> frozenset[str]:
        parts: list[str] = []
        for rec in trace.recommendations:
            for cf in rec.counterfactuals:
                parts.append(f"{rec.zone_id}:{cf.intervention.value}:{cf.counterfactual_state.value}")
        return frozenset(parts)

    scores: list[float] = []
    prev = signature(traces[0])
    for trace in traces[1:]:
        current = signature(trace)
        union = prev | current
        inter = prev & current
        scores.append(len(inter) / len(union) if union else 1.0)
        prev = current
    return sum(scores) / len(scores) if scores else 1.0


def build_counterfactual_trace(
    *,
    scenario_id: str,
    seed: int,
    recommendations: list[CounterfactualRecommendation],
    stability: float = 1.0,
) -> CounterfactualTrace:
    from datetime import UTC, datetime

    consistency, _, coverage = aggregate_trace_metrics(recommendations)
    return CounterfactualTrace(
        scenario_id=scenario_id,
        seed=seed,
        generated_at=datetime.now(tz=UTC),
        recommendations=tuple(recommendations),
        counterfactual_consistency=round(consistency, 4),
        counterfactual_stability=round(stability, 4),
        counterfactual_explanation_coverage=round(coverage, 4),
    )


__all__ = [
    "aggregate_trace_metrics",
    "build_counterfactual_trace",
    "counterfactual_consistency_for_recommendation",
    "counterfactual_explanation_coverage",
    "counterfactual_stability_across_traces",
]
