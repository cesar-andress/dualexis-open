"""Local LLM reasoning schemas — structured events only, no raw media."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dualexis.schemas.common import EventId, utc_now
from dualexis.schemas.domain import SafetyEvent


class ReasoningConfidence(StrEnum):
    """Confidence tier for reasoning output."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendedAction(StrEnum):
    """Human-in-the-loop recommended actions — never autonomous enforcement."""

    MONITOR = "monitor"
    NOTIFY_STAFF = "notify_staff"
    REQUEST_REVIEW = "request_review"
    ESCALATE = "escalate"
    NO_ACTION = "no_action"


class ReasoningRequest(BaseModel):
    """Request for local reasoning over structured event context."""

    model_config = ConfigDict()

    request_id: str
    event: SafetyEvent
    context_events: tuple[SafetyEvent, ...] = Field(default_factory=tuple)
    max_tokens: int = Field(default=512, ge=64, le=4096)


class ReasoningResponse(BaseModel):
    """Explainable reasoning output for human decision support."""

    model_config = ConfigDict()

    request_id: str
    event_id: EventId
    timestamp: datetime = Field(default_factory=utc_now)
    summary: str = Field(min_length=1, max_length=1024)
    explanation: str = Field(min_length=1, max_length=4096)
    confidence: ReasoningConfidence
    recommended_action: RecommendedAction
    requires_human_review: bool = True
    model_id: str = Field(default="placeholder-local-llm")
