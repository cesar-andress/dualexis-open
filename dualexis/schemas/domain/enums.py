"""Domain enumerations for event-centric safety orchestration."""

from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    """Semantic category of a safety-related event — zone-level, not identity-based."""

    ACOUSTIC_ANOMALY = "acoustic_anomaly"
    CROWD_ACTIVITY = "crowd_activity"
    ENVIRONMENTAL_SENSOR = "environmental_sensor"
    MULTIMODAL_FUSION = "multimodal_fusion"
    ZONE_ACTIVITY = "zone_activity"
    UNKNOWN = "unknown"


class PrivacyLevel(StrEnum):
    """Data sensitivity tier for event payloads."""

    EPHEMERAL = "ephemeral"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class RetentionPolicy(StrEnum):
    """Retention tier for structured event metadata."""

    EPHEMERAL = "ephemeral"
    SHORT = "short"
    STANDARD = "standard"
    NONE = "none"


class HumanReviewStatus(StrEnum):
    """Human-in-the-loop review lifecycle for significant events."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class OrchestrationAction(StrEnum):
    """Advisory orchestration actions — never autonomous enforcement."""

    MONITOR = "monitor"
    NOTIFY_STAFF = "notify_staff"
    REQUEST_REVIEW = "request_review"
    ESCALATE = "escalate"
    NO_ACTION = "no_action"
