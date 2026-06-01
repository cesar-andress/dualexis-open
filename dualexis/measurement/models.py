"""Measurement data models for DUALEXIS benchmarks."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MeasurementKind(StrEnum):
    """Supported measurement command categories."""

    SCENARIO = "scenario"
    LATENCY = "latency"
    PRIVACY = "privacy"
    ROBUSTNESS = "robustness"
    ALL = "all"


class MeasurementMetrics(BaseModel):
    """Collected measurement metrics for a scenario run."""

    model_config = ConfigDict(frozen=True)

    end_to_end_latency_ms: float = Field(ge=0.0)
    event_generation_latency_ms: float = Field(ge=0.0)
    fusion_latency_ms: float = Field(ge=0.0)
    graph_update_latency_ms: float = Field(ge=0.0)
    reasoning_latency_ms: float = Field(ge=0.0)
    recommendation_latency_ms: float = Field(ge=0.0)
    number_of_events: int = Field(ge=0)
    number_of_recommendations: int = Field(ge=0)
    privacy_violation_count: int = Field(ge=0)
    raw_media_retention_score: float = Field(ge=0.0, le=1.0)
    personal_data_exposure_score: float = Field(ge=0.0, le=1.0)
    human_review_compliance_rate: float = Field(ge=0.0, le=1.0)
    modality_drop_tolerance: float = Field(ge=0.0, le=1.0)
    deterministic_reproducibility_score: float = Field(ge=0.0, le=1.0)


class MeasurementReport(BaseModel):
    """Structured measurement output for CLI export."""

    model_config = ConfigDict(frozen=True)

    kind: MeasurementKind
    scenario: str = Field(min_length=1, max_length=64)
    seed: int
    runs: int = Field(default=1, ge=1)
    metrics: MeasurementMetrics
    generated_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class CombinedMeasurementReport(BaseModel):
    """Bundle produced by ``measure all``."""

    model_config = ConfigDict(frozen=True)

    scenario: str = Field(min_length=1, max_length=64)
    seed: int
    runs: int = Field(ge=1)
    scenario_report: MeasurementReport
    latency_report: MeasurementReport
    privacy_report: MeasurementReport
    robustness_report: MeasurementReport
    generated_at: datetime


__all__ = [
    "CombinedMeasurementReport",
    "MeasurementKind",
    "MeasurementMetrics",
    "MeasurementReport",
]
