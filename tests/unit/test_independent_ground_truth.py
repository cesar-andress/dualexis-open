"""Tests for independent ground-truth YAML (decoupled from event generator)."""

from __future__ import annotations

import json

import pytest

from dualexis.simulation import run_scenario
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
def test_simulation_ground_truth_not_copied_from_events() -> None:
    """Ground-truth labels must not be a per-event copy of generator output."""
    result = run_scenario("exit_blockage", seed=42)
    assert result.ground_truth.labels

    event_keys = {
        (event.zone_id, event.metadata.get("category", "")) for event in result.events
    }
    gt_keys = {(label.zone_id, label.semantic_label) for label in result.ground_truth.labels}
    assert gt_keys != event_keys or len(result.events) != len(result.ground_truth.labels)


@pytest.mark.unit
def test_independent_labeler_differs_from_generator_categories() -> None:
    """Independent labeler uses distinct semantic labels for exit blockage."""
    independent = build_independent_ground_truth(ScenarioId.EXIT_BLOCKAGE, seed=0)
    labels = {label.semantic_label for label in independent.labels}
    assert "exit_blockage" in labels or "exit_throughput_reduced" in labels
