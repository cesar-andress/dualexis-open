"""Ontology drift detection models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class OntologyLayer(StrEnum):
    """Tracked ontology layers."""

    SEMANTIC_LABEL = "semantic_label"
    SAFETY_STATE = "safety_state"
    RECOMMENDATION = "recommendation"


class OntologySnapshot(BaseModel):
    """Ontology vocabulary observed for one (scenario, seed, version) cell."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1, max_length=64)
    seed: int
    version: str = Field(min_length=1, max_length=32)
    semantic_labels: tuple[str, ...] = Field(default_factory=tuple)
    safety_states: tuple[str, ...] = Field(default_factory=tuple)
    recommendations: tuple[str, ...] = Field(default_factory=tuple)


class ScenarioDriftMetrics(BaseModel):
    """Drift metrics for one scenario (across seeds at a version)."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    version: str
    semantic_drift: float = Field(ge=0.0, le=1.0)
    safety_state_drift: float = Field(ge=0.0, le=1.0)
    recommendation_drift: float = Field(ge=0.0, le=1.0)
    ontology_stability: float = Field(ge=0.0, le=1.0)


class VersionOntologySummary(BaseModel):
    """Aggregated vocabulary for one benchmark version."""

    model_config = ConfigDict(frozen=True)

    version: str
    semantic_labels: tuple[str, ...] = Field(default_factory=tuple)
    safety_states: tuple[str, ...] = Field(default_factory=tuple)
    recommendations: tuple[str, ...] = Field(default_factory=tuple)
    snapshot_count: int = Field(ge=0)


class OntologyDriftReport(BaseModel):
    """Full ontology drift audit."""

    model_config = ConfigDict(frozen=True)

    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    versions: tuple[str, ...] = Field(default_factory=tuple)
    seeds: tuple[int, ...] = Field(default_factory=tuple)
    scenarios: tuple[str, ...] = Field(default_factory=tuple)
    snapshots: tuple[OntologySnapshot, ...] = Field(default_factory=tuple)
    per_scenario: tuple[ScenarioDriftMetrics, ...] = Field(default_factory=tuple)
    version_summaries: tuple[VersionOntologySummary, ...] = Field(default_factory=tuple)
    ontology_stability: float = Field(ge=0.0, le=1.0)
    semantic_drift: float = Field(ge=0.0, le=1.0)
    recommendation_drift: float = Field(ge=0.0, le=1.0)
    cross_version_semantic_drift: float = Field(ge=0.0, le=1.0, default=0.0)
    registry_warnings: tuple[str, ...] = Field(default_factory=tuple)
    disclaimer: str = Field(min_length=1)


__all__ = [
    "OntologyDriftReport",
    "OntologyLayer",
    "OntologySnapshot",
    "ScenarioDriftMetrics",
    "VersionOntologySummary",
]
