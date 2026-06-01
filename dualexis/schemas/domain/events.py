"""Event-centric domain models for DUALEXIS safety orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from dualexis.schemas.common import EventId, utc_now
from dualexis.schemas.domain.enums import (
    EventType,
    HumanReviewStatus,
    OrchestrationAction,
    PrivacyLevel,
    RetentionPolicy,
)
from dualexis.schemas.domain.validators import (
    validate_label_tuple,
    validate_metadata_dict,
)
from dualexis.schemas.domain.values import ConfidenceScore, EventSource, LocationReference
from dualexis.schemas.lifecycle import EventSeverity, EventStatus, SemanticDescriptor


class OrchestrationRecommendation(BaseModel):
    """Explainable advisory output for human-in-the-loop response support."""

    model_config = ConfigDict(frozen=True)

    action: OrchestrationAction
    confidence: ConfidenceScore
    explanation: str = Field(min_length=1, max_length=4096)
    requires_human_approval: bool = True


class NormalizedEvent(BaseModel):
    """Privacy-preserving event produced after perception normalization."""

    model_config = ConfigDict()

    event_id: EventId = Field(default_factory=uuid4)
    source: EventSource
    location: LocationReference
    event_type: EventType
    confidence: ConfidenceScore
    labels: tuple[str, ...] = Field(default_factory=tuple)
    privacy_level: PrivacyLevel = PrivacyLevel.EPHEMERAL
    retention: RetentionPolicy = RetentionPolicy.EPHEMERAL
    explanation: str = Field(min_length=1, max_length=4096)
    observed_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return validate_label_tuple(value)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata_dict(value)


class FusionResult(BaseModel):
    """Explainable output of multimodal semantic fusion."""

    model_config = ConfigDict()

    fusion_id: str = Field(min_length=1, max_length=64)
    source: EventSource
    location: LocationReference
    confidence: ConfidenceScore
    fused_labels: tuple[str, ...] = Field(min_length=1)
    explanation: str = Field(min_length=1, max_length=4096)
    signal_ids: tuple[str, ...] = Field(default_factory=tuple)
    modality_contributions: dict[str, float] = Field(default_factory=dict)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    timestamp: datetime = Field(default_factory=utc_now)

    @field_validator("fused_labels")
    @classmethod
    def validate_fused_labels(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return validate_label_tuple(value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fused_confidence(self) -> float:
        """Backward-compatible alias for fusion confidence value."""
        return self.confidence.value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def node_id(self) -> str:
        return self.source.node_id

    @computed_field  # type: ignore[prop-decorator]
    @property
    def zone_id(self) -> str:
        return self.location.zone_id


class SafetyEvent(BaseModel):
    """Core safety event — structured, explainable, and privacy-preserving."""

    model_config = ConfigDict()

    event_id: EventId = Field(default_factory=uuid4)
    source: EventSource
    location: LocationReference
    event_type: EventType
    severity: EventSeverity
    confidence: ConfidenceScore
    explanation: str = Field(min_length=1, max_length=4096)
    timestamp: datetime = Field(default_factory=utc_now)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    retention: RetentionPolicy = RetentionPolicy.STANDARD
    human_review: HumanReviewStatus = HumanReviewStatus.NOT_REQUIRED
    recommendation: OrchestrationRecommendation | None = None
    status: EventStatus = EventStatus.DETECTED
    descriptors: tuple[SemanticDescriptor, ...] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata_dict(value)

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_flat_fields(cls, data: Any) -> Any:
        """Accept legacy flat ``node_id`` / ``zone_id`` construction during migration."""
        if not isinstance(data, dict):
            return data
        if "source" in data or "location" in data:
            return data

        legacy = dict(data)
        node_id = legacy.pop("node_id", None)
        zone_id = legacy.pop("zone_id", None)
        if node_id is None or zone_id is None:
            return legacy

        legacy.setdefault(
            "source",
            {"node_id": node_id, "modality": "multimodal", "pipeline_id": "legacy"},
        )
        legacy.setdefault(
            "location",
            {"zone_id": zone_id, "zone_label": f"zone-{zone_id}"},
        )
        legacy.setdefault("event_type", EventType.MULTIMODAL_FUSION.value)

        if "confidence" not in legacy:
            score: float | None = legacy.pop("fusion_score", None)
            if score is None and legacy.get("descriptors"):
                first = legacy["descriptors"][0]
                if isinstance(first, dict):
                    score = float(first.get("confidence", 0.5))
                else:
                    score = float(getattr(first, "confidence", 0.5))
            legacy["confidence"] = {
                "value": float(score if score is not None else 0.5),
                "rationale": "Coerced from legacy event construction",
            }

        if "explanation" not in legacy:
            legacy["explanation"] = legacy.pop(
                "summary",
                "Safety event generated from legacy pipeline output",
            )

        if "requires_human_review" in legacy:
            requires_review = legacy.pop("requires_human_review")
            if requires_review:
                legacy.setdefault("human_review", HumanReviewStatus.PENDING.value)
            else:
                legacy.setdefault("human_review", HumanReviewStatus.NOT_REQUIRED.value)

        return legacy

    @computed_field  # type: ignore[prop-decorator]
    @property
    def node_id(self) -> str:
        return self.source.node_id

    @computed_field  # type: ignore[prop-decorator]
    @property
    def zone_id(self) -> str:
        return self.location.zone_id

    @computed_field  # type: ignore[prop-decorator]
    @property
    def requires_human_review(self) -> bool:
        return self.human_review in {
            HumanReviewStatus.PENDING,
            HumanReviewStatus.IN_PROGRESS,
        }


class FusedEvent(SafetyEvent):
    """Safety event enriched by multimodal fusion."""

    fusion_score: float = Field(ge=0.0, le=1.0)
    contributing_signals: tuple[str, ...] = Field(default_factory=tuple)
    status: EventStatus = EventStatus.FUSED

    @model_validator(mode="after")
    def align_fusion_score_with_confidence(self) -> FusedEvent:
        if abs(self.fusion_score - self.confidence.value) > 1e-6:
            object.__setattr__(
                self,
                "confidence",
                self.confidence.model_copy(
                    update={
                        "value": self.fusion_score,
                        "rationale": self.confidence.rationale,
                    }
                ),
            )
        return self
