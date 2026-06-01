"""Run counterfactual analysis over simulation scenarios."""

from __future__ import annotations

from dualexis.counterfactual.metrics import (
    build_counterfactual_trace,
    counterfactual_stability_across_traces,
)
from dualexis.counterfactual.models import (
    CounterfactualEvaluationReport,
    CounterfactualRecommendation,
    CounterfactualTrace,
)
from dualexis.counterfactual.reasoning import (
    build_counterfactual_recommendation,
    synthesize_recommendation_from_trace,
)
from dualexis.pipeline import run_pipeline
from dualexis.pipeline.config import PipelineRunConfig
from dualexis.sssg.runner import build_sssg_trace_from_scenario

COUNTERFACTUAL_PIPELINE_CONFIG = PipelineRunConfig(
    enable_privacy_runtime=True,
    enable_temporal_graph=True,
    enable_explanation_layer=True,
    enable_sssg=True,
)


def collect_counterfactual_recommendations(
    scenario_id: str,
    *,
    seed: int,
) -> list[CounterfactualRecommendation]:
    """Run pipeline + SSSG and attach what-if scenarios to each recommendation."""
    output = run_pipeline(
        scenario_id,
        seed=seed,
        run_config=COUNTERFACTUAL_PIPELINE_CONFIG,
    )
    trace = output.state_transition_trace or build_sssg_trace_from_scenario(
        scenario_id, seed=seed
    )

    cf_recommendations: list[CounterfactualRecommendation] = []
    pipeline_recs = list(output.recommendations)

    if not pipeline_recs:
        for zone_id in trace.zone_ids or trace.final_states:
            synthetic = synthesize_recommendation_from_trace(trace, zone_id=zone_id)
            if synthetic is not None:
                pipeline_recs.append(synthetic)

    for recommendation in pipeline_recs:
        cf_rec = build_counterfactual_recommendation(
            recommendation,
            trace,
            scenario_id=scenario_id,
            seed=seed,
        )
        if cf_rec is not None:
            cf_recommendations.append(cf_rec)

    return cf_recommendations


def evaluate_counterfactual_scenario(
    scenario_id: str,
    *,
    seed: int,
    stability: float = 1.0,
) -> CounterfactualTrace:
    recommendations = collect_counterfactual_recommendations(scenario_id, seed=seed)
    return build_counterfactual_trace(
        scenario_id=scenario_id,
        seed=seed,
        recommendations=recommendations,
        stability=stability,
    )


def evaluate_counterfactual_battery(
    scenarios: tuple[str, ...],
    *,
    seeds: tuple[int, ...] = (1, 2, 3),
) -> CounterfactualEvaluationReport:
    traces: list[CounterfactualTrace] = []
    by_scenario: dict[str, list[CounterfactualTrace]] = {}

    for scenario in scenarios:
        scenario_traces: list[CounterfactualTrace] = []
        for seed in seeds:
            scenario_traces.append(evaluate_counterfactual_scenario(scenario, seed=seed))
        stability = counterfactual_stability_across_traces(scenario_traces)
        updated = [
            t.model_copy(update={"counterfactual_stability": round(stability, 4)})
            for t in scenario_traces
        ]
        by_scenario[scenario] = updated
        traces.extend(updated)

    if not traces:
        return CounterfactualEvaluationReport(
            traces=(),
            mean_counterfactual_consistency=1.0,
            mean_counterfactual_stability=1.0,
            mean_counterfactual_explanation_coverage=0.0,
            recommendation_count=0,
        )

    flat = [t for group in by_scenario.values() for t in group]
    rec_count = sum(len(t.recommendations) for t in flat)
    return CounterfactualEvaluationReport(
        traces=tuple(flat),
        mean_counterfactual_consistency=round(
            sum(t.counterfactual_consistency for t in flat) / len(flat), 4
        ),
        mean_counterfactual_stability=round(
            sum(t.counterfactual_stability for t in flat) / len(flat), 4
        ),
        mean_counterfactual_explanation_coverage=round(
            sum(t.counterfactual_explanation_coverage for t in flat) / len(flat), 4
        ),
        recommendation_count=rec_count,
    )


__all__ = [
    "COUNTERFACTUAL_PIPELINE_CONFIG",
    "collect_counterfactual_recommendations",
    "evaluate_counterfactual_battery",
    "evaluate_counterfactual_scenario",
]
