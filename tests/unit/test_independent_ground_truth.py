"""Tests for independent ground-truth YAML (decoupled from event generator)."""

from __future__ import annotations

from collections import Counter

import pytest

from dualexis.simulation import run_scenario
from dualexis.simulation.emission_mode import EmissionMode
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.independent_labeler import build_independent_ground_truth
from dualexis.simulation.scenario import ScenarioId


@pytest.mark.unit
@pytest.mark.parametrize("scenario_name", [scenario.value for scenario in ScenarioId])
def test_independent_ground_truth_yaml_loads(scenario_name: str) -> None:
    loaded = load_scenario_ground_truth(ScenarioId(scenario_name))
    assert loaded.primary_label
    assert loaded.scenario_id.value == scenario_name


@pytest.mark.unit
def test_simulation_events_align_with_procedural_rules_via_separate_modules() -> None:
    """Emitter and labeler share rule definitions but remain separate code paths."""
    result = run_scenario(
        "exit_blockage",
        seed=42,
        emission_mode=EmissionMode.SHARED_SPEC,
    )
    built = build_independent_ground_truth(ScenarioId.EXIT_BLOCKAGE, seed=42)
    event_keys = Counter(
        (event.zone_id, event.metadata.get("category", "")) for event in result.events
    )
    label_keys = Counter((label.zone_id, label.semantic_label) for label in built.labels)
    assert event_keys == label_keys


@pytest.mark.unit
def test_independent_labeler_exit_blockage_vocabulary() -> None:
    """Independent labeler exposes exit blockage procedural labels."""
    independent = build_independent_ground_truth(ScenarioId.EXIT_BLOCKAGE, seed=0)
    labels = {label.semantic_label for label in independent.labels}
    assert "exit_blockage" in labels
    assert "exit_throughput_reduced" in labels
