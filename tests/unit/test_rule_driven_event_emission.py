"""Regression tests for rule-driven simulator event emission vs procedural GT."""

from __future__ import annotations

import ast
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dualexis.evaluation.comparable_baselines import DualexisFullPipelineBaseline
from dualexis.evaluation.metrics import (
    compute_event_detection_accuracy,
    compute_false_positive_rate,
    count_false_positives_and_negatives,
    events_for_b5_alignment,
)
from dualexis.pipeline import run_pipeline
from dualexis.simulation.emission_mode import EmissionMode
from dualexis.simulation import run_scenario
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.independent_labeler import build_independent_ground_truth, labels_for_tick
from dualexis.simulation.rule_driven_emitter import emit_rule_driven_events
from dualexis.simulation.scenario import ScenarioId, get_scenario_definition
from dualexis.simulation.world import build_default_world, initial_world_state
from dualexis.simulation.world_dynamics import advance_world_state


def _simulator_events(scenario: str, *, seed: int) -> tuple:
    result = run_scenario(
        scenario,
        seed=seed,
        emission_mode=EmissionMode.SHARED_SPEC,
    )
    return tuple(
        event for event in result.events if event.source.value == "simulator"
    )


def _label_key_counts(labels) -> Counter[tuple[str, str]]:
    return Counter((label.zone_id, label.semantic_label) for label in labels)


def _event_key_counts(events) -> Counter[tuple[str, str]]:
    return Counter((event.zone_id, event.metadata.get("category", "")) for event in events)


@pytest.mark.unit
def test_rule_driven_emitter_has_no_independent_labeler_import() -> None:
    module_path = (
        Path(__file__).resolve().parents[2] / "dualexis/simulation/rule_driven_emitter.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("independent_labeler" in name for name in imports)


@pytest.mark.unit
def test_emitter_matches_independent_labeler_keys_for_all_scenarios() -> None:
    for scenario_id in ScenarioId:
        result = run_scenario(
            scenario_id.value,
            seed=17,
            emission_mode=EmissionMode.SHARED_SPEC,
        )
        built = build_independent_ground_truth(scenario_id, seed=17)
        assert _event_key_counts(result.events) == _label_key_counts(built.labels)


@pytest.mark.unit
def test_normal_flow_has_no_false_positive_simulator_events() -> None:
    events = _simulator_events("normal_flow", seed=1)
    procedural = build_independent_ground_truth(ScenarioId.NORMAL_FLOW, seed=1)
    fp, fn = count_false_positives_and_negatives(events, procedural)
    assert fp == 0
    assert fn == 0
    assert compute_false_positive_rate(events, procedural) == 0.0


@pytest.mark.unit
def test_exit_blockage_emits_throughput_and_blockage_labels() -> None:
    events = _simulator_events("exit_blockage", seed=1)
    categories = {event.metadata.get("category") for event in events}
    assert "exit_blockage" in categories
    assert "exit_throughput_reduced" in categories

    procedural = build_independent_ground_truth(ScenarioId.EXIT_BLOCKAGE, seed=1)
    assert _event_key_counts(events) == _label_key_counts(procedural.labels)
    assert compute_event_detection_accuracy(events, procedural) == 1.0


@pytest.mark.unit
def test_multimodal_conflict_uses_gt_vocabulary() -> None:
    events = _simulator_events("multimodal_conflict", seed=1)
    categories = {event.metadata.get("category") for event in events}
    assert "multimodal_conflict" in categories
    assert "conflicting_signals" not in categories

    procedural = build_independent_ground_truth(ScenarioId.MULTIMODAL_CONFLICT, seed=1)
    assert compute_event_detection_accuracy(events, procedural) == 1.0


@pytest.mark.unit
def test_evacuation_respects_max_zones_per_tick() -> None:
    scenario_id = ScenarioId.EVACUATION_RECOMMENDATION
    definition = get_scenario_definition(scenario_id)
    rng = random.Random(3)
    graph = build_default_world()
    state = initial_world_state(graph)
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

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
        tick_events = emit_rule_driven_events(
            state,
            scenario_id=scenario_id,
            tick_seconds=definition.tick_seconds,
            node_id="sim-edge-001",
            start_time=start_time,
        )
        assert len(tick_events) <= 2
        assert len(tick_events) == len(tick_labels)
        if state.tick >= 3:
            assert {event.zone_id for event in tick_events}.issubset({"cafeteria", "exit-lobby"})

    events = _simulator_events("evacuation_recommendation", seed=3)
    categories = {event.metadata.get("category") for event in events}
    assert categories == {"evacuation_stress_pattern"}
    assert all(event.zone_id in {"cafeteria", "exit-lobby"} for event in events)


@pytest.mark.unit
def test_crowd_acceleration_covers_gt_tick_range() -> None:
    events = _simulator_events("crowd_acceleration", seed=1)
    ticks = {int(event.metadata["tick"]) for event in events}
    assert ticks == set(range(3, 13))

    categories = {event.metadata.get("category") for event in events}
    assert categories == {"crowd_density_elevated"}
    assert "density_elevated" not in categories

    procedural = build_independent_ground_truth(ScenarioId.CROWD_ACCELERATION, seed=1)
    assert compute_event_detection_accuracy(events, procedural) == 1.0


@pytest.mark.unit
def test_audio_stress_covers_gt_tick_range() -> None:
    events = _simulator_events("audio_stress_signal", seed=1)
    ticks = {int(event.metadata["tick"]) for event in events}
    assert ticks == set(range(2, 13))

    categories = {event.metadata.get("category") for event in events}
    assert categories == {"acoustic_stress"}
    assert "elevated_sound_level" not in categories

    procedural = build_independent_ground_truth(ScenarioId.AUDIO_STRESS_SIGNAL, seed=1)
    assert compute_event_detection_accuracy(events, procedural) == 1.0


@pytest.mark.unit
def test_b5_excludes_pipeline_multimodal_fusion_placeholder() -> None:
    output = run_pipeline("normal_flow", seed=1)
    filtered = events_for_b5_alignment(output.normalized_events)
    categories = {event.metadata.get("category") for event in filtered}
    assert "multimodal_fusion" not in categories
    assert "normal_flow" in categories


@pytest.mark.unit
@pytest.mark.parametrize("scenario", [scenario.value for scenario in ScenarioId])
def test_b5_full_pipeline_decoupled_par_above_floor(scenario: str) -> None:
    """Pipeline B5 alignment under decoupled emission is not required to be 1.0."""
    baseline = DualexisFullPipelineBaseline()
    result = baseline.run_once(scenario, seed=1)
    assert 0.65 <= result.event_detection_accuracy <= 1.0


@pytest.mark.unit
def test_frozen_ground_truth_yaml_unchanged_reference() -> None:
    """Frozen seed-0 YAML remains the published reference export."""
    loaded = load_scenario_ground_truth(ScenarioId.EXIT_BLOCKAGE)
    assert any(label.semantic_label == "exit_throughput_reduced" for label in loaded.labels)
