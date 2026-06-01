"""Unit tests for the reproducible DUALEXIS simulation environment."""

from __future__ import annotations

import json

import pytest

from dualexis.privacy_runtime.models import FORBIDDEN_BIOMETRIC_KEYS, FORBIDDEN_IDENTITY_TERMS
from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation import ScenarioId, run_scenario
from dualexis.simulation.runner import SimulationRunner
from dualexis.simulation.scenario import SCENARIO_DEFINITIONS, UnknownScenarioError


@pytest.mark.unit
@pytest.mark.parametrize("scenario_name", [scenario.value for scenario in ScenarioId])
def test_all_scenarios_run_and_emit_events(scenario_name: str) -> None:
    result = run_scenario(scenario_name, seed=42)
    assert result.scenario_id.value == scenario_name
    assert result.seed == 42
    assert len(result.events) > 0
    assert result.ground_truth.scenario_id.value == scenario_name
    expected_label = SCENARIO_DEFINITIONS[ScenarioId(scenario_name)].expected_ground_truth_label
    assert result.ground_truth.primary_label == expected_label


@pytest.mark.unit
def test_known_scenarios_exist() -> None:
    expected = {
        "normal_flow",
        "crowd_acceleration",
        "exit_blockage",
        "audio_stress_signal",
        "multimodal_conflict",
        "evacuation_recommendation",
    }
    assert {scenario.value for scenario in ScenarioId} == expected


@pytest.mark.unit
def test_invalid_scenario_raises_clean_error() -> None:
    with pytest.raises(UnknownScenarioError, match="Unknown scenario 'not_a_scenario'"):
        run_scenario("not_a_scenario", seed=42)


@pytest.mark.unit
def test_reproducibility_same_seed_same_events() -> None:
    a = run_scenario("crowd_acceleration", seed=99)
    b = run_scenario("crowd_acceleration", seed=99)
    dumps_a = [event.model_dump(mode="json") for event in a.events]
    dumps_b = [event.model_dump(mode="json") for event in b.events]
    assert dumps_a == dumps_b


@pytest.mark.unit
def test_different_seeds_may_differ() -> None:
    a = run_scenario("exit_blockage", seed=1)
    b = run_scenario("exit_blockage", seed=2)
    assert a.events != b.events or a.final_state != b.final_state


@pytest.mark.unit
def test_world_models_confined_space_topology() -> None:
    result = run_scenario("normal_flow", seed=7)
    zone_ids = {zone.zone_id for zone in result.graph.zones}
    assert zone_ids == {"hallway-a", "cafeteria", "exit-lobby"}
    exit_ids = {exit_node.exit_id for exit_node in result.graph.exits}
    assert exit_ids == {"exit-north", "exit-main"}
    assert len(result.graph.edges) == 2


@pytest.mark.unit
def test_flow_entities_are_anonymous_not_identities() -> None:
    result = run_scenario("normal_flow", seed=7)
    assert result.final_state is not None
    for entity in result.final_state.flow_entities:
        assert entity.entity_id.startswith("flow-")
        lowered = entity.entity_id.lower()
        for term in FORBIDDEN_IDENTITY_TERMS:
            assert term not in lowered


@pytest.mark.unit
def test_events_are_valid_semantic_events_without_forbidden_fields() -> None:
    result = run_scenario("multimodal_conflict", seed=42)
    for event in result.events:
        assert isinstance(event, SemanticEvent)
        assert event.raw_media_persisted is False
        assert event.source.value == "simulator"
        dumped = json.dumps(event.model_dump(mode="json"))
        lowered = dumped.lower()
        for key in FORBIDDEN_BIOMETRIC_KEYS:
            assert key not in lowered
        assert "raw_video" not in lowered
        assert "raw_audio" not in lowered
        assert "payload_ref" not in lowered


@pytest.mark.unit
def test_events_have_timestamps_and_zone_ids() -> None:
    result = run_scenario("audio_stress_signal", seed=42)
    ticks = {label.tick for label in result.ground_truth.labels}
    assert ticks
    for event in result.events:
        assert event.timestamp is not None
        assert event.zone_id
        assert event.metadata.get("category")


@pytest.mark.unit
def test_ground_truth_recommends_review_for_high_risk_scenarios() -> None:
    result = run_scenario("evacuation_recommendation", seed=42)
    assert result.ground_truth.recommended_review is True


@pytest.mark.unit
def test_scenario_specific_labels() -> None:
    crowd = run_scenario("crowd_acceleration", seed=42)
    categories = {event.metadata.get("category") for event in crowd.events}
    assert "density_elevated" in categories

    audio = run_scenario("audio_stress_signal", seed=42)
    audio_cats = {event.metadata.get("category") for event in audio.events}
    assert "elevated_sound_level" in audio_cats


@pytest.mark.unit
def test_runner_custom_location() -> None:
    result = SimulationRunner(
        scenario_id=ScenarioId.NORMAL_FLOW,
        seed=1,
        location_id="custom-site",
    ).run()
    assert result.graph.location_id == "custom-site"
