"""End-to-end pipeline data models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dualexis.orchestration.models import OrchestrationRecommendation
from dualexis.privacy_runtime.report import PrivacyReport
from dualexis.sssg.models import StateTransitionTrace
from dualexis.schemas.audit import AuditEntry
from dualexis.schemas.domain import FusionResult
from dualexis.schemas.domain.validators import validate_metadata_dict
from dualexis.semantic_events.models import SemanticEvent


class PipelineSourceType(StrEnum):
    """Synthetic source channel for pipeline inputs (no live media)."""

    SIMULATOR = "simulator"
    SYNTHETIC_EDGE = "synthetic_edge"
    MANUAL_FIXTURE = "manual_fixture"


class GraphUpdate(BaseModel):
    """Recorded temporal graph mutation."""

    model_config = ConfigDict(frozen=True)

    update_type: str = Field(min_length=1, max_length=32)
    event_id: UUID
    details: dict[str, str] = Field(default_factory=dict)


class PipelineInput(BaseModel):
    """Synthetic local signal batch entering the pipeline."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(min_length=1, max_length=64)
    source_type: PipelineSourceType
    timestamp: datetime
    synthetic_payload: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("metadata", "synthetic_payload")
    @classmethod
    def validate_string_maps(cls, value: dict[str, str]) -> dict[str, str]:
        validate_metadata_dict(value)
        return value


class PipelineOutput(BaseModel):
    """Artifacts produced by a full pipeline execution."""

    model_config = ConfigDict(frozen=True)

    normalized_events: tuple[SemanticEvent, ...] = Field(default_factory=tuple)
    fusion_result: FusionResult | None = None
    graph_updates: tuple[GraphUpdate, ...] = Field(default_factory=tuple)
    recommendations: tuple[OrchestrationRecommendation, ...] = Field(default_factory=tuple)
    audit_records: tuple[AuditEntry, ...] = Field(default_factory=tuple)
    privacy_report: PrivacyReport
    state_transition_trace: StateTransitionTrace | None = None


__all__ = [
    "GraphUpdate",
    "PipelineInput",
    "PipelineOutput",
    "PipelineSourceType",
    "PrivacyReport",
    "StateTransitionTrace",
]
