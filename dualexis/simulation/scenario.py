"""Scenario definitions for reproducible confined-space simulation.

Maps to DUALEXIS formal model scenarios (Section methodology / evaluation).
No real personal data, video, or biometrics are used.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ScenarioId(StrEnum):
    """Initial reproducible simulation scenarios."""

    NORMAL_FLOW = "normal_flow"
    CROWD_ACCELERATION = "crowd_acceleration"
    EXIT_BLOCKAGE = "exit_blockage"
    AUDIO_STRESS_SIGNAL = "audio_stress_signal"
    MULTIMODAL_CONFLICT = "multimodal_conflict"
    EVACUATION_RECOMMENDATION = "evacuation_recommendation"


class ScenarioDefinition(BaseModel):
    """Declarative scenario parameters for deterministic replay."""

    model_config = ConfigDict(frozen=True)

    scenario_id: ScenarioId
    description: str = Field(min_length=1, max_length=512)
    duration_steps: int = Field(default=12, ge=1, le=1000)
    tick_seconds: float = Field(default=1.0, gt=0.0, le=60.0)
    expected_ground_truth_label: str = Field(min_length=1, max_length=128)


SCENARIO_DEFINITIONS: dict[ScenarioId, ScenarioDefinition] = {
    ScenarioId.NORMAL_FLOW: ScenarioDefinition(
        scenario_id=ScenarioId.NORMAL_FLOW,
        description="Steady anonymous flow across zones with baseline activity.",
        expected_ground_truth_label="normal_operations",
    ),
    ScenarioId.CROWD_ACCELERATION: ScenarioDefinition(
        scenario_id=ScenarioId.CROWD_ACCELERATION,
        description="Rising aggregate density in cafeteria without identity tracking.",
        expected_ground_truth_label="crowd_density_elevated",
    ),
    ScenarioId.EXIT_BLOCKAGE: ScenarioDefinition(
        scenario_id=ScenarioId.EXIT_BLOCKAGE,
        description="Exit throughput reduced; flow accumulates upstream.",
        expected_ground_truth_label="exit_blockage",
    ),
    ScenarioId.AUDIO_STRESS_SIGNAL: ScenarioDefinition(
        scenario_id=ScenarioId.AUDIO_STRESS_SIGNAL,
        description="Synthetic acoustic stress indicator in hallway (no raw audio).",
        expected_ground_truth_label="acoustic_stress",
    ),
    ScenarioId.MULTIMODAL_CONFLICT: ScenarioDefinition(
        scenario_id=ScenarioId.MULTIMODAL_CONFLICT,
        description="Conflicting synthetic video vs audio zone descriptors.",
        expected_ground_truth_label="multimodal_conflict",
    ),
    ScenarioId.EVACUATION_RECOMMENDATION: ScenarioDefinition(
        scenario_id=ScenarioId.EVACUATION_RECOMMENDATION,
        description="Multi-zone stress pattern suggesting staff review for evacuation.",
        expected_ground_truth_label="evacuation_review",
    ),
}


def get_scenario_definition(scenario_id: ScenarioId) -> ScenarioDefinition:
    """Return the definition for a built-in scenario."""
    return SCENARIO_DEFINITIONS[scenario_id]


class UnknownScenarioError(ValueError):
    """Raised when a scenario name is not registered."""


def resolve_scenario(name: str) -> ScenarioId:
    """Resolve a scenario string to ``ScenarioId`` or raise ``UnknownScenarioError``."""
    try:
        return ScenarioId(name)
    except ValueError as exc:
        valid = ", ".join(s.value for s in ScenarioId)
        msg = f"Unknown scenario {name!r}. Valid scenarios: {valid}"
        raise UnknownScenarioError(msg) from exc
