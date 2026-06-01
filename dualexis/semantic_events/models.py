"""Core semantic event domain models (L3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel
from dualexis.schemas.domain.validators import contains_forbidden_term, validate_metadata_dict


class EventType(StrEnum):
    """Taxonomy of zone-scoped safety-relevant semantic events."""

    NORMAL_FLOW = "normal_flow"
    CROWD_ACCELERATION = "crowd_acceleration"
    EXIT_BLOCKAGE = "exit_blockage"
    AUDIO_STRESS_SIGNAL = "audio_stress_signal"
    FALL_DETECTED = "fall_detected"
    MULTIMODAL_CONFLICT = "multimodal_conflict"
    EVACUATION_SIGNAL = "evacuation_signal"
    UNKNOWN = "unknown"


class EventSource(StrEnum):
    """Provenance channel for a semantic event — no identity-bearing metadata."""

    VIDEO_EDGE_NODE = "video_edge_node"
    AUDIO_EDGE_NODE = "audio_edge_node"
    SENSOR_NODE = "sensor_node"
    SIMULATOR = "simulator"
    MANUAL_REPORT = "manual_report"


class SemanticEvent(BaseModel):
    """Normalized, explainable safety event — the primary L3 reasoning artifact."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    event_type: EventType
    source: EventSource
    zone_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    severity: SeverityLevel
    explanation: str = Field(min_length=1, max_length=2048)
    privacy_level: PrivacyLevel
    raw_media_persisted: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("zone_id", "explanation")
    @classmethod
    def reject_identity_terms(cls, value: str) -> str:
        matched = contains_forbidden_term(value)
        if matched is not None:
            msg = f"Field contains forbidden term '{matched}'"
            raise ValueError(msg)
        return value

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        validate_metadata_dict(value)
        return value

    @field_validator("raw_media_persisted")
    @classmethod
    def reject_persistent_raw_media(cls, value: bool) -> bool:
        if value:
            msg = (
                "raw_media_persisted must remain False — "
                "DUALEXIS does not persist raw media by default"
            )
            raise ValueError(msg)
        return value


@dataclass(frozen=True, slots=True)
class LayerMetadata:
    """Static metadata for the Semantic Event Layer."""

    layer_id: str = "L3"
    name: str = "Semantic Event Layer"
    processes_events_only: bool = True


SEMANTIC_EVENTS_LAYER = LayerMetadata()


__all__ = [
    "SEMANTIC_EVENTS_LAYER",
    "EventSource",
    "EventType",
    "LayerMetadata",
    "SemanticEvent",
]
