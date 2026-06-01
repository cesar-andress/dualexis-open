"""Multiseed robustness audit orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from dualexis.experiments.sssg_battery import PAPER_SCENARIOS
from dualexis.robustness.models import (
    MetricDistribution,
    RobustnessAuditReport,
    ScenarioRobustness,
    StabilityMetricKind,
)
from dualexis.robustness.signatures import SeedSignatures, collect_signatures
from dualexis.robustness.stability import (
    compute_robustness_score,
    distribution_from_values,
    mean_pairwise_jaccard,
    per_seed_reference_stability,
)

_METRIC_KEYS: tuple[tuple[str, StabilityMetricKind], ...] = (
    ("event", StabilityMetricKind.EVENT),
    ("state", StabilityMetricKind.STATE),
    ("recommendation", StabilityMetricKind.RECOMMENDATION),
    ("explanation", StabilityMetricKind.EXPLANATION),
)


def audit_scenario_robustness(
    scenario_id: str,
    seeds: tuple[int, ...],
) -> ScenarioRobustness:
    """Measure four stability dimensions for one scenario across seeds."""
    signatures: dict[str, dict[int, frozenset[str]]] = {
        key: {} for key, _ in _METRIC_KEYS
    }
    for seed in seeds:
        collected: SeedSignatures = collect_signatures(scenario_id, seed)
        signatures["event"][seed] = collected.event
        signatures["state"][seed] = collected.state
        signatures["recommendation"][seed] = collected.recommendation
        signatures["explanation"][seed] = collected.explanation

    distributions: list[MetricDistribution] = []
    per_seed_vs_reference: dict[int, dict[str, float]] = {seed: {} for seed in seeds}
    stability_values: dict[str, float] = {}

    for key, kind in _METRIC_KEYS:
        sigs = [signatures[key][seed] for seed in seeds]
        pairwise = mean_pairwise_jaccard(sigs)
        per_seed = per_seed_reference_stability(signatures[key], seeds)
        dist = distribution_from_values(kind, per_seed)
        distributions.append(dist)
        stability_values[key] = round(pairwise, 4)
        for seed, value in zip(seeds, per_seed, strict=True):
            per_seed_vs_reference[seed][key] = round(value, 4)

    return ScenarioRobustness(
        scenario_id=scenario_id,
        seeds=seeds,
        event_stability=stability_values["event"],
        state_stability=stability_values["state"],
        recommendation_stability=stability_values["recommendation"],
        explanation_stability=stability_values["explanation"],
        distributions=tuple(distributions),
        per_seed_vs_reference=per_seed_vs_reference,
    )


def run_robustness_audit(
    *,
    seeds: tuple[int, ...],
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
) -> RobustnessAuditReport:
    """Run full multiseed robustness audit."""
    scenario_results: list[ScenarioRobustness] = []
    for scenario in scenarios:
        scenario_results.append(audit_scenario_robustness(scenario, seeds))

    aggregate: list[MetricDistribution] = []
    for _key, kind in _METRIC_KEYS:
        attr = {
            StabilityMetricKind.EVENT: "event_stability",
            StabilityMetricKind.STATE: "state_stability",
            StabilityMetricKind.RECOMMENDATION: "recommendation_stability",
            StabilityMetricKind.EXPLANATION: "explanation_stability",
        }[kind]
        values = [getattr(scenario, attr) for scenario in scenario_results]
        aggregate.append(distribution_from_values(kind, values))

    robustness_score = compute_robustness_score(aggregate)

    return RobustnessAuditReport(
        generated_at=datetime.now(tz=UTC),
        seeds=seeds,
        scenarios=tuple(scenario_results),
        aggregate_distributions=tuple(aggregate),
        robustness_score=robustness_score,
    )


__all__ = ["audit_scenario_robustness", "run_robustness_audit"]
