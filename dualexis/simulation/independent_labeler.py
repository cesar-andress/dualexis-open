"""Independent ground-truth labeler (decoupled from ``SyntheticEventGenerator``).

Labels are derived from anonymous world-state metrics via YAML rules in
``experiments/ground_truth/rules/``. Authored labels are stored in
``experiments/ground_truth/*.yaml`` for evaluation.
"""

from __future__ import annotations

import random

from dualexis.orchestration.models import SeverityLevel
from dualexis.simulation.ground_truth import GroundTruthLabel, ScenarioGroundTruth
from dualexis.simulation.gt_rules import load_ground_truth_rules, rule_matches_tick
from dualexis.simulation.scenario import ScenarioId, get_scenario_definition
from dualexis.simulation.world import build_default_world, initial_world_state
from dualexis.simulation.world_dynamics import advance_world_state


def _severity_from_metrics(density: float, activity: float, audio: float) -> SeverityLevel:
    score = min(1.0, 0.4 * density + 0.35 * activity + 0.25 * audio)
    if score >= 0.82:
        return SeverityLevel.HIGH
    if score >= 0.62:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def labels_for_tick(
    scenario_id: ScenarioId,
    *,
    tick: int,
    zone_density: dict[str, float],
    zone_activity: dict[str, float],
    zone_audio: dict[str, float],
    exit_throughput: dict[str, float],
) -> tuple[GroundTruthLabel, ...]:
    """Return independent labels for one tick using external YAML rules."""
    rules_doc = load_ground_truth_rules(scenario_id)
    emitted: list[GroundTruthLabel] = []
    seen: set[tuple[int, str, str]] = set()

    for rule in rules_doc.label_rules:
        zone_ids = rule_matches_tick(
            rule,
            tick=tick,
            zone_density=zone_density,
            zone_activity=zone_activity,
            zone_audio=zone_audio,
            exit_throughput=exit_throughput,
        )
        for zone_id in zone_ids:
            key = (tick, zone_id, rule.semantic_label)
            if key in seen:
                continue
            seen.add(key)
            density = zone_density.get(zone_id, 0.0)
            activity = zone_activity.get(zone_id, 0.0)
            audio = zone_audio.get(zone_id, 0.0)
            emitted.append(
                GroundTruthLabel(
                    scenario_id=scenario_id,
                    tick=tick,
                    zone_id=zone_id,
                    semantic_label=rule.semantic_label,
                    expected_severity=_severity_from_metrics(density, activity, audio),
                    expected_event_type=rule.expected_event_type,
                    notes=f"e2_rules:{rules_doc.version}",
                )
            )
    return tuple(emitted)


def build_independent_ground_truth(
    scenario_id: ScenarioId,
    *,
    seed: int = 0,
    location_id: str = "gt-reference-site",
) -> ScenarioGroundTruth:
    """Walk world dynamics and accumulate labels (reference seed for YAML export)."""
    definition = get_scenario_definition(scenario_id)
    rng = random.Random(seed)
    graph = build_default_world(location_id=location_id)
    state = initial_world_state(graph)
    all_labels: list[GroundTruthLabel] = []

    for _step in range(definition.duration_steps):
        state = advance_world_state(state, graph, definition, scenario_id, rng)
        tick_labels = labels_for_tick(
            scenario_id,
            tick=state.tick,
            zone_density=state.zone_density,
            zone_activity=state.zone_activity,
            zone_audio=state.zone_audio_stress,
            exit_throughput=state.exit_throughput,
        )
        all_labels.extend(tick_labels)

    definition_meta = get_scenario_definition(scenario_id)
    return ScenarioGroundTruth(
        scenario_id=scenario_id,
        primary_label=definition_meta.expected_ground_truth_label,
        labels=tuple(all_labels),
        recommended_review=scenario_id
        in {
            ScenarioId.EVACUATION_RECOMMENDATION,
            ScenarioId.EXIT_BLOCKAGE,
            ScenarioId.MULTIMODAL_CONFLICT,
        },
    )


__all__ = [
    "build_independent_ground_truth",
    "labels_for_tick",
]
