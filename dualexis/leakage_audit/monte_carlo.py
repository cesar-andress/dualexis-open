"""Monte Carlo threshold perturbation for E2 leakage sensitivity."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from dualexis.evaluation.metrics import count_false_positives_and_negatives
from dualexis.simulation import run_scenario
from dualexis.simulation.ground_truth import GroundTruthLabel, ScenarioGroundTruth
from dualexis.simulation.gt_rules import (
    GroundTruthRulesDocument,
    LabelRule,
    RuleCondition,
    load_ground_truth_rules,
    rule_matches_tick,
)
from dualexis.simulation.independent_labeler import _severity_from_metrics, build_independent_ground_truth
from dualexis.simulation.scenario import ScenarioId, get_scenario_definition
from dualexis.simulation.world import build_default_world, initial_world_state
from dualexis.simulation.world_dynamics import advance_world_state


@dataclass(frozen=True)
class MonteCarloScenarioResult:
    """Aggregated MC outcomes for one scenario."""

    scenario_id: str
    ground_truth_stability: float
    event_stability: float
    agreement_drift: float


def _perturb_rules(
    doc: GroundTruthRulesDocument,
    rng: random.Random,
    *,
    scale_range: tuple[float, float] = (0.88, 1.12),
) -> GroundTruthRulesDocument:
    new_rules: list[LabelRule] = []
    for rule in doc.label_rules:
        new_conditions: list[RuleCondition] = []
        for cond in rule.conditions:
            scale = rng.uniform(*scale_range)
            new_value = max(0.01, min(0.99, cond.value * scale))
            new_conditions.append(cond.model_copy(update={"value": round(new_value, 4)}))
        new_rules.append(rule.model_copy(update={"conditions": tuple(new_conditions)}))
    return doc.model_copy(update={"label_rules": tuple(new_rules)})


def _labels_signature(ground_truth: ScenarioGroundTruth) -> Counter[tuple[str, str, int]]:
    return Counter(
        (label.zone_id, label.semantic_label, label.tick) for label in ground_truth.labels
    )


def _baseline_agreement(scenario: str, *, seed: int) -> float:
    result = run_scenario(scenario, seed=seed)
    fp, fn = count_false_positives_and_negatives(result.events, result.ground_truth)
    total = len(result.ground_truth.labels) + len(result.events)
    if total == 0:
        return 1.0
    errors = fp + fn
    return max(0.0, 1.0 - errors / total)


def _ground_truth_with_rules(
    scenario_id: ScenarioId,
    *,
    seed: int,
    rules_doc: GroundTruthRulesDocument,
) -> ScenarioGroundTruth:
    """Walk dynamics applying supplied rules document (inline, no YAML write)."""
    definition = get_scenario_definition(scenario_id)
    rng = random.Random(seed)
    graph = build_default_world(location_id="mc-audit")
    state = initial_world_state(graph)
    all_labels = []

    for _step in range(definition.duration_steps):
        state = advance_world_state(state, graph, definition, scenario_id, rng)
        tick_labels = []
        for rule in rules_doc.label_rules:
            zone_ids = rule_matches_tick(
                rule,
                tick=state.tick,
                zone_density=state.zone_density,
                zone_activity=state.zone_activity,
                zone_audio=state.zone_audio_stress,
                exit_throughput=state.exit_throughput,
            )
            seen: set[tuple[int, str, str]] = set()
            for zone_id in zone_ids:
                key = (state.tick, zone_id, rule.semantic_label)
                if key in seen:
                    continue
                seen.add(key)
                density = state.zone_density.get(zone_id, 0.0)
                activity = state.zone_activity.get(zone_id, 0.0)
                audio = state.zone_audio_stress.get(zone_id, 0.0)
                tick_labels.append(
                    GroundTruthLabel(
                        scenario_id=scenario_id,
                        tick=state.tick,
                        zone_id=zone_id,
                        semantic_label=rule.semantic_label,
                        expected_severity=_severity_from_metrics(density, activity, audio),
                        expected_event_type=rule.expected_event_type,
                        notes="mc_perturbed",
                    )
                )
        all_labels.extend(tick_labels)

    meta = get_scenario_definition(scenario_id)
    return ScenarioGroundTruth(
        scenario_id=scenario_id,
        primary_label=meta.expected_ground_truth_label,
        labels=tuple(all_labels),
        recommended_review=scenario_id
        in {
            ScenarioId.EVACUATION_RECOMMENDATION,
            ScenarioId.EXIT_BLOCKAGE,
            ScenarioId.MULTIMODAL_CONFLICT,
        },
    )


def run_monte_carlo_scenario(
    scenario: str,
    *,
    seed: int = 1,
    iterations: int = 1000,
    mc_seed: int = 42,
) -> MonteCarloScenarioResult:
    scenario_id = ScenarioId(scenario)
    baseline_gt = build_independent_ground_truth(scenario_id, seed=seed)
    baseline_sig = _labels_signature(baseline_gt)
    sim_baseline = run_scenario(scenario, seed=seed)
    baseline_events = sim_baseline.events
    baseline_event_keys = {
        (e.zone_id, e.metadata.get("category", ""), e.timestamp.isoformat()) for e in baseline_events
    }
    baseline_agreement = _baseline_agreement(scenario, seed=seed)
    rules_base = load_ground_truth_rules(scenario_id)

    rng = random.Random(mc_seed)
    gt_stabilities: list[float] = []
    event_stabilities: list[float] = []
    agreement_drifts: list[float] = []

    for _ in range(iterations):
        perturbed = _perturb_rules(rules_base, rng)
        perturbed_gt = _ground_truth_with_rules(scenario_id, seed=seed, rules_doc=perturbed)
        perturbed_sig = _labels_signature(perturbed_gt)

        union = baseline_sig + perturbed_sig
        inter = baseline_sig & perturbed_sig
        union_mass = sum(union.values()) or 1
        inter_mass = sum(inter.values())
        gt_stabilities.append(inter_mass / union_mass)

        # Events unchanged under GT-only perturbation (generator not perturbed in this audit)
        if baseline_event_keys:
            event_stabilities.append(1.0)
        else:
            event_stabilities.append(1.0)

        fp, fn = count_false_positives_and_negatives(baseline_events, perturbed_gt)
        total = len(perturbed_gt.labels) + len(baseline_events) or 1
        perturbed_agreement = max(0.0, 1.0 - (fp + fn) / total)
        agreement_drifts.append(abs(baseline_agreement - perturbed_agreement))

    return MonteCarloScenarioResult(
        scenario_id=scenario,
        ground_truth_stability=sum(gt_stabilities) / len(gt_stabilities),
        event_stability=sum(event_stabilities) / len(event_stabilities),
        agreement_drift=sum(agreement_drifts) / len(agreement_drifts),
    )


def run_monte_carlo_battery(
    scenarios: tuple[str, ...],
    *,
    seed: int = 1,
    iterations: int = 1000,
) -> dict[str, MonteCarloScenarioResult]:
    return {
        scenario: run_monte_carlo_scenario(scenario, seed=seed, iterations=iterations)
        for scenario in scenarios
    }


__all__ = [
    "MonteCarloScenarioResult",
    "run_monte_carlo_battery",
    "run_monte_carlo_scenario",
]
