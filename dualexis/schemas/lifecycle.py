"""Event lifecycle types and semantic descriptors."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dualexis.schemas.domain.validators import validate_evidence_dict


class EventSeverity(StrEnum):
    """Severity levels for safety events."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(StrEnum):
    """Lifecycle status of a safety event."""

    DETECTED = "detected"
    FUSED = "fused"
    REASONED = "reasoned"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class SemanticDescriptor(BaseModel):
    """Explainable semantic content attached to an event."""

    model_config = ConfigDict(frozen=True)

    category: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=512)
    confidence: float = Field(ge=0.0, le=1.0)
    source_modalities: tuple[str, ...] = Field(default_factory=tuple)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence")
    @classmethod
    def no_raw_media(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_evidence_dict(value)
