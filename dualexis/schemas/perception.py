"""Perception signal schemas — zone-level, non-biometric descriptors only."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dualexis.schemas.common import NodeId, ZoneId, utc_now


class Modality(StrEnum):
    """Supported perception modalities."""

    VIDEO = "video"
    AUDIO = "audio"
    SENSOR = "sensor"


class ZoneDescriptor(BaseModel):
    """Anonymized spatial zone descriptor — no individual identity."""

    model_config = ConfigDict(frozen=True, strict=True)

    zone_id: ZoneId
    label: str = Field(min_length=1, max_length=128)
    occupancy_estimate: int = Field(ge=0, le=10000)
    activity_level: float = Field(ge=0.0, le=1.0, description="Normalized activity intensity")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_biometric_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"face", "facial", "biometric", "identity", "person_id", "student_id"}
        for key in value:
            if any(term in key.lower() for term in forbidden):
                msg = f"Biometric or identity key '{key}' is not permitted in zone descriptors"
                raise ValueError(msg)
        return value


class PerceptionSignal(BaseModel):
    """Structured output from an edge perception pipeline."""

    model_config = ConfigDict(frozen=True, strict=True)

    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    modality: Modality
    node_id: NodeId
    timestamp: datetime = Field(default_factory=utc_now)
    zone: ZoneDescriptor
    confidence: float = Field(ge=0.0, le=1.0)
    labels: tuple[str, ...] = Field(default_factory=tuple)
    features: dict[str, float] = Field(default_factory=dict)

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        forbidden_terms = {"face", "identity", "person_name", "student"}
        for label in value:
            lower = label.lower()
            if any(term in lower for term in forbidden_terms):
                msg = f"Label '{label}' contains forbidden identity-related terms"
                raise ValueError(msg)
        return value


class PerceptionFrame(BaseModel):
    """Ephemeral input frame — never persisted by the framework."""

    model_config = ConfigDict()

    frame_id: str = Field(default_factory=lambda: str(uuid4()))
    modality: Modality
    node_id: NodeId
    zone_id: ZoneId
    timestamp: datetime = Field(default_factory=utc_now)
    duration_ms: int = Field(default=0, ge=0)
    payload_ref: str | None = Field(
        default=None,
        description="In-memory buffer reference; not a filesystem path",
    )
