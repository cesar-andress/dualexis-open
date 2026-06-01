"""Privacy runtime domain models (L1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dualexis.schemas.domain.enums import RetentionPolicy as EventRetentionTier
from dualexis.schemas.domain.validators import contains_forbidden_term

# Explicit forbidden payload fields (exact key match, case-insensitive).
FORBIDDEN_BIOMETRIC_FIELDS: frozenset[str] = frozenset(
    {
        "face_id",
        "biometric_hash",
        "facial_embedding",
        "face_embedding",
        "voiceprint",
        "voice_print",
    }
)

FORBIDDEN_IDENTITY_FIELDS: frozenset[str] = frozenset(
    {
        "person_id",
        "student_id",
        "identity",
        "name",
        "surname",
        "national_id",
    }
)

FORBIDDEN_MEDIA_FIELDS: frozenset[str] = frozenset(
    {
        "raw_video_path",
        "raw_audio_path",
        "raw_video",
        "raw_audio",
        "frame_data",
        "media_url",
        "persistent_media_ref",
    }
)

MEDIA_STRIP_FIELDS: frozenset[str] = FORBIDDEN_MEDIA_FIELDS | frozenset({"payload_ref"})

FORBIDDEN_FIELDS: frozenset[str] = (
    FORBIDDEN_BIOMETRIC_FIELDS | FORBIDDEN_IDENTITY_FIELDS | FORBIDDEN_MEDIA_FIELDS
)

# Backward-compatible aliases used by framework constraint tests.
FORBIDDEN_BIOMETRIC_KEYS: frozenset[str] = FORBIDDEN_BIOMETRIC_FIELDS | frozenset(
    {"face", "facial", "biometric", "speaker_id"}
)
FORBIDDEN_IDENTITY_TERMS: frozenset[str] = FORBIDDEN_IDENTITY_FIELDS | frozenset(
    {"face", "person_name", "student", "speaker_id"}
)
FORBIDDEN_MEDIA_EVIDENCE_KEYS: frozenset[str] = FORBIDDEN_MEDIA_FIELDS


def normalize_field_key(key: str) -> str:
    """Normalize a payload key for forbidden-field lookup."""
    return key.lower().replace("-", "_")


def is_forbidden_field(key: str) -> bool:
    """Return True when *key* matches a forbidden biometric, identity, or media field."""
    normalized = normalize_field_key(key)
    if normalized in FORBIDDEN_FIELDS:
        return True
    return contains_forbidden_term(key) is not None


class PrivacyLevel(StrEnum):
    """Data minimization tier for stored and transmitted artifacts."""

    EPHEMERAL = "ephemeral"
    SEMANTIC_ONLY = "semantic_only"
    AGGREGATED = "aggregated"
    AUDIT_ONLY = "audit_only"


class RetentionPolicy(BaseModel):
    """Privacy-first retention contract for media, events, and audit records."""

    model_config = ConfigDict(frozen=True)

    raw_media_retention_seconds: int = Field(default=0, ge=0)
    semantic_event_retention_days: int = Field(ge=1)
    audit_retention_days: int = Field(ge=1)
    allow_raw_media_storage: bool = False

    @model_validator(mode="after")
    def enforce_raw_media_constraints(self) -> RetentionPolicy:
        if not self.allow_raw_media_storage and self.raw_media_retention_seconds != 0:
            msg = "raw_media_retention_seconds must be 0 unless allow_raw_media_storage is True"
            raise ValueError(msg)
        return self


DEFAULT_RETENTION_POLICY = RetentionPolicy(
    raw_media_retention_seconds=0,
    semantic_event_retention_days=30,
    audit_retention_days=365,
    allow_raw_media_storage=False,
)


class PrivacyPolicy(BaseModel):
    """Declarative privacy policy enforced by the L1 privacy runtime."""

    model_config = ConfigDict(frozen=True, strict=True)

    policy_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    raw_video_retention_seconds: int = Field(default=0, ge=0)
    raw_audio_retention_seconds: int = Field(default=0, ge=0)
    semantic_event_retention_days: int = Field(default=30, ge=1)
    audit_retention_days: int = Field(default=365, ge=1)
    allow_persistent_media: bool = False
    allow_biometric_features: bool = False
    allow_identity_linking: bool = False
    allow_cross_zone_tracking: bool = False
    max_buffer_ttl: timedelta = Field(default=timedelta(seconds=30))
    event_retention: EventRetentionTier = EventRetentionTier.STANDARD
    gdpr_lawful_basis: str = Field(
        default="legitimate_interest",
        description="Documented lawful basis under GDPR Article 6",
    )

    @model_validator(mode="after")
    def enforce_strict_defaults(self) -> PrivacyPolicy:
        if self.allow_biometric_features:
            msg = "Biometric features are prohibited in DUALEXIS by design"
            raise ValueError(msg)
        if not self.allow_persistent_media:
            if self.raw_video_retention_seconds != 0:
                msg = "raw_video_retention_seconds must be 0 unless persistent media is allowed"
                raise ValueError(msg)
            if self.raw_audio_retention_seconds != 0:
                msg = "raw_audio_retention_seconds must be 0 unless persistent media is allowed"
                raise ValueError(msg)
        if self.allow_persistent_media and self.max_buffer_ttl > timedelta(minutes=5):
            msg = "Persistent media requires buffer TTL <= 5 minutes"
            raise ValueError(msg)
        return self


class PrivacyViolationType(StrEnum):
    """Category of privacy constraint breach."""

    BIOMETRIC = "biometric"
    IDENTITY = "identity"
    MEDIA = "media"
    POLICY = "policy"
    AUDIT = "audit"


class PrivacyViolation(BaseModel):
    """Structured record of a privacy constraint violation."""

    model_config = ConfigDict(frozen=True)

    violation_id: str = Field(default_factory=lambda: str(uuid4()))
    field_name: str = Field(min_length=1, max_length=128)
    violation_type: PrivacyViolationType
    message: str = Field(min_length=1, max_length=1024)
    boundary: str | None = None


class TrustBoundary(StrEnum):
    """Trust boundary identifiers for privacy enforcement (TB1--TB5)."""

    TB1_EPHEMERAL_BUFFER = "tb1_ephemeral_buffer"
    TB2_PERCEPTION_OUTPUT = "tb2_perception_output"
    TB3_EVENT_PUBLICATION = "tb3_event_publication"
    TB4_LLM_REASONING = "tb4_llm_reasoning"
    TB5_NETWORK_EGRESS = "tb5_network_egress"


class PrivacyCheckResult(StrEnum):
    """Outcome of a privacy guard evaluation."""

    PASSED = "passed"
    FAILED = "failed"


class RetentionDecision(BaseModel):
    """Outcome of applying retention policy to an artifact."""

    model_config = ConfigDict(frozen=True)

    artifact_kind: str
    may_retain: bool
    retention_seconds: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=512)


@dataclass(frozen=True, slots=True)
class LayerMetadata:
    """Static metadata for the Privacy Runtime Layer."""

    layer_id: str = "L1"
    name: str = "Privacy Runtime Layer"
    processes_events_only: bool = True


PRIVACY_RUNTIME_LAYER = LayerMetadata()


def classify_forbidden_field(key: str) -> PrivacyViolationType:
    """Classify a forbidden field key into a violation type."""
    normalized = normalize_field_key(key)
    if normalized in FORBIDDEN_BIOMETRIC_FIELDS or contains_forbidden_term(key) == "biometric":
        return PrivacyViolationType.BIOMETRIC
    if normalized in FORBIDDEN_IDENTITY_FIELDS:
        return PrivacyViolationType.IDENTITY
    if normalized in FORBIDDEN_MEDIA_FIELDS:
        return PrivacyViolationType.MEDIA
    matched = contains_forbidden_term(key)
    if matched in {"face", "facial", "face_embedding", "voice_print", "speaker_id"}:
        return PrivacyViolationType.BIOMETRIC
    if matched in {"identity", "person_name", "student", "speaker_id"}:
        return PrivacyViolationType.IDENTITY
    return PrivacyViolationType.POLICY


def iter_payload_keys(payload: dict[str, Any], *, prefix: str = "") -> list[str]:
    """Return dotted paths for all keys in a nested payload mapping."""
    paths: list[str] = []
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        paths.append(path)
        if isinstance(value, dict):
            paths.extend(iter_payload_keys(value, prefix=path))
    return paths


__all__ = [
    "DEFAULT_RETENTION_POLICY",
    "FORBIDDEN_BIOMETRIC_FIELDS",
    "FORBIDDEN_BIOMETRIC_KEYS",
    "FORBIDDEN_FIELDS",
    "FORBIDDEN_IDENTITY_FIELDS",
    "FORBIDDEN_IDENTITY_TERMS",
    "FORBIDDEN_MEDIA_EVIDENCE_KEYS",
    "FORBIDDEN_MEDIA_FIELDS",
    "MEDIA_STRIP_FIELDS",
    "PRIVACY_RUNTIME_LAYER",
    "EventRetentionTier",
    "LayerMetadata",
    "PrivacyCheckResult",
    "PrivacyLevel",
    "PrivacyPolicy",
    "PrivacyViolation",
    "PrivacyViolationType",
    "RetentionDecision",
    "RetentionPolicy",
    "TrustBoundary",
    "classify_forbidden_field",
    "is_forbidden_field",
    "iter_payload_keys",
    "normalize_field_key",
]
