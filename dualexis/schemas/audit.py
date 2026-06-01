"""Audit trail schemas for compliance and explainability."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from dualexis.schemas.common import EventId, NodeId, utc_now


class AuditAction(StrEnum):
    """Auditable actions within the DUALEXIS pipeline."""

    PERCEPTION_PROCESSED = "perception_processed"
    FUSION_COMPLETED = "fusion_completed"
    REASONING_INVOKED = "reasoning_invoked"
    EVENT_PUBLISHED = "event_published"
    PRIVACY_CHECK_PASSED = "privacy_check_passed"
    PRIVACY_CHECK_FAILED = "privacy_check_failed"
    HUMAN_REVIEW = "human_review"
    POLICY_UPDATED = "policy_updated"


class AuditEntry(BaseModel):
    """Append-only audit record — metadata only, no raw sensor payloads."""

    model_config = ConfigDict(frozen=True, strict=True)

    entry_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    action: AuditAction
    node_id: NodeId | None = None
    event_id: EventId | None = None
    actor: str = Field(default="system", max_length=128)
    details: dict[str, Any] = Field(default_factory=dict)
    integrity_hash: str | None = Field(
        default=None,
        description="SHA-256 hash for tamper detection (computed at write time)",
    )
