"""Ground-truth labels for simulation scenarios.

Used for benchmark evaluation; no personal data.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from dualexis.orchestration.models import SeverityLevel
from dualexis.semantic_events.models import EventType
from dualexis.simulation.scenario import ScenarioId


class GroundTruthLabel(BaseModel):
    """Expected semantic label for a simulation timestep or segment."""

    model_config = ConfigDict(frozen=True)

    scenario_id: ScenarioId
    tick: int = Field(ge=0)
    zone_id: str = Field(min_length=1, max_length=64)
    semantic_label: str = Field(min_length=1, max_length=128)
    expected_severity: SeverityLevel = SeverityLevel.LOW
    expected_event_type: EventType
    notes: str = Field(default="", max_length=512)


class ScenarioGroundTruth(BaseModel):
    """Aggregate ground truth for a full simulation run."""

    model_config = ConfigDict(frozen=True)

    scenario_id: ScenarioId
    primary_label: str = Field(min_length=1, max_length=128)
    labels: tuple[GroundTruthLabel, ...] = Field(default_factory=tuple)
    recommended_review: bool = False
