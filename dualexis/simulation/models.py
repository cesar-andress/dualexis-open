"""Simulation layer — data models for synthetic scenario generation.

Maps to DUALEXIS simulation / benchmark tooling (no real occupant media).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dualexis.schemas.perception import Modality, PerceptionFrame
from dualexis.simulation.scenario import ScenarioId


@dataclass(frozen=True)
class LayerMetadata:
    """Static descriptor for the simulation benchmark layer."""

    layer_id: str = "SIM"
    name: str = "simulation"
    processes_events_only: bool = True


SIMULATION_LAYER = LayerMetadata()

__all__ = [
    "SIMULATION_LAYER",
    "LayerMetadata",
    "ScenarioId",
    "SimulationScenario",
    "SyntheticFrameBatch",
    "build_synthetic_batch",
]


class SimulationScenario(StrEnum):
    """Legacy scenario identifiers (kept for backward compatibility)."""

    HALLWAY_ACOUSTIC = "hallway_acoustic"
    CAFETERIA_CROWD = "cafeteria_crowd"
    EXIT_ENVIRONMENTAL = "exit_environmental"
    MULTIMODAL_CORRELATED = "multimodal_correlated"


class SyntheticFrameBatch(BaseModel):
    """Batch of ephemeral synthetic frames for pipeline testing."""

    model_config = ConfigDict(frozen=True)

    scenario: SimulationScenario
    node_id: str = Field(min_length=1, max_length=64)
    zone_id: str = Field(min_length=1, max_length=64)
    frames: tuple[PerceptionFrame, ...] = Field(min_length=1)


def build_synthetic_batch(
    scenario: SimulationScenario,
    *,
    node_id: str = "sim-edge-001",
    zone_id: str = "hallway-a",
) -> SyntheticFrameBatch:
    """Build a deterministic synthetic frame batch without raw media storage."""
    frames: tuple[PerceptionFrame, ...]
    if scenario == SimulationScenario.HALLWAY_ACOUSTIC:
        frames = (PerceptionFrame(modality=Modality.AUDIO, node_id=node_id, zone_id=zone_id),)
    elif scenario == SimulationScenario.CAFETERIA_CROWD:
        frames = (PerceptionFrame(modality=Modality.VIDEO, node_id=node_id, zone_id=zone_id),)
    elif scenario == SimulationScenario.EXIT_ENVIRONMENTAL:
        frames = (PerceptionFrame(modality=Modality.SENSOR, node_id=node_id, zone_id=zone_id),)
    else:
        frames = (
            PerceptionFrame(modality=Modality.VIDEO, node_id=node_id, zone_id=zone_id),
            PerceptionFrame(modality=Modality.AUDIO, node_id=node_id, zone_id=zone_id),
            PerceptionFrame(modality=Modality.SENSOR, node_id=node_id, zone_id=zone_id),
        )
    return SyntheticFrameBatch(scenario=scenario, node_id=node_id, zone_id=zone_id, frames=frames)
