"""Orchestration domain models (L6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SeverityLevel(StrEnum):
    """Operational severity for events and orchestration recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HumanReviewStatus(StrEnum):
    """Lifecycle state for human-in-the-loop review of recommendations."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


HIGH_RISK_SEVERITIES: frozenset[str] = frozenset(
    {SeverityLevel.HIGH.value, SeverityLevel.CRITICAL.value}
)

_REVIEW_REQUIRED_SEVERITIES: frozenset[SeverityLevel] = frozenset(
    {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
)


class OrchestrationRecommendation(BaseModel):
    """Advisory orchestration output subject to human review when severity is elevated."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: UUID
    based_on_events: list[UUID] = Field(min_length=1)
    target_zone_id: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=256)
    rationale: str = Field(min_length=1, max_length=2048)
    severity: SeverityLevel
    requires_human_review: bool
    human_review_status: HumanReviewStatus
    created_at: datetime

    @model_validator(mode="after")
    def enforce_human_review_rules(self) -> OrchestrationRecommendation:
        if self.severity in _REVIEW_REQUIRED_SEVERITIES:
            if not self.requires_human_review:
                msg = f"severity {self.severity.value} requires requires_human_review=True"
                raise ValueError(msg)
            if self.human_review_status == HumanReviewStatus.APPROVED:
                msg = (
                    f"severity {self.severity.value} recommendations "
                    "cannot start with human_review_status=APPROVED"
                )
                raise ValueError(msg)
        return self


class OrchestrationPhase(StrEnum):
    """High-level orchestration pipeline phase."""

    INGEST = "ingest"
    FUSE = "fuse"
    GRAPH = "graph"
    REASON = "reason"
    REVIEW = "review"
    PUBLISH = "publish"


@dataclass(frozen=True, slots=True)
class LayerMetadata:
    """Static metadata for the Orchestration Layer."""

    layer_id: str = "L6"
    name: str = "Human-in-the-Loop Orchestration Layer"
    processes_events_only: bool = True


ORCHESTRATION_LAYER = LayerMetadata()


__all__ = [
    "HIGH_RISK_SEVERITIES",
    "ORCHESTRATION_LAYER",
    "HumanReviewStatus",
    "LayerMetadata",
    "OrchestrationPhase",
    "OrchestrationRecommendation",
    "SeverityLevel",
]
