"""Backward-compatible re-exports for event schemas."""

from dualexis.schemas.domain.events import FusedEvent, SafetyEvent
from dualexis.schemas.lifecycle import EventSeverity, EventStatus, SemanticDescriptor

__all__ = [
    "EventSeverity",
    "EventStatus",
    "FusedEvent",
    "SafetyEvent",
    "SemanticDescriptor",
]
