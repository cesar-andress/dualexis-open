"""Longitudinal safety narrative models (TSGG-backed)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class NarrativeStageKind(StrEnum):
    """TSGG stages represented in a longitudinal narrative."""

    EVIDENCE = "evidence"
    STATE_CHANGE = "state_change"
    RECOMMENDATION = "recommendation"
    GOVERNANCE = "governance"
    STABILIZATION = "stabilization"


class NarrativeBeat(BaseModel):
    """One timestamped line in a safety narrative."""

    model_config = ConfigDict(frozen=True)

    clock_label: str = Field(min_length=4, max_length=8, description="HH:MM display time")
    tick: int = Field(ge=0)
    stage: NarrativeStageKind
    text: str = Field(min_length=1, max_length=512)
    zone_id: str = Field(min_length=1, max_length=64)
    source_id: str = Field(default="", max_length=128)


class NarrativeMetrics(BaseModel):
    """Quality descriptors for one narrative trace."""

    model_config = ConfigDict(frozen=True)

    narrative_completeness: float = Field(ge=0.0, le=1.0)
    narrative_consistency: float = Field(ge=0.0, le=1.0)
    narrative_fidelity: float = Field(ge=0.0, le=1.0)


class NarrativeTrace(BaseModel):
    """Longitudinal explanation of safety evolution for one zone."""

    model_config = ConfigDict(frozen=True)

    trace_id: UUID = Field(default_factory=uuid4)
    scenario_id: str = Field(min_length=1, max_length=64)
    seed: int
    zone_id: str = Field(min_length=1, max_length=64)
    beats: tuple[NarrativeBeat, ...] = Field(default_factory=tuple)
    metrics: NarrativeMetrics
    rendered_text: str = Field(min_length=1)


class LongitudinalNarrativeReport(BaseModel):
    """Batch of narrative traces from TSGG runs."""

    model_config = ConfigDict(frozen=True)

    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    traces: tuple[NarrativeTrace, ...] = Field(default_factory=tuple)
    mean_completeness: float = Field(ge=0.0, le=1.0)
    mean_consistency: float = Field(ge=0.0, le=1.0)
    mean_fidelity: float = Field(ge=0.0, le=1.0)
    disclaimer: str = Field(min_length=1)


NARRATIVE_DISCLAIMER = (
    "Longitudinal safety narratives are synthesized from synthetic TSGG traces for "
    "explanatory audit. They describe evolution of confined-space situations, not "
    "verified incident timelines."
)


__all__ = [
    "NARRATIVE_DISCLAIMER",
    "LongitudinalNarrativeReport",
    "NarrativeBeat",
    "NarrativeMetrics",
    "NarrativeStageKind",
    "NarrativeTrace",
]
