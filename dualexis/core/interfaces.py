"""Abstract interfaces for DUALEXIS subsystems (legacy re-exports).

New framework-layer ABCs live in dualexis.<layer>.interfaces.
These aliases preserve backward compatibility for existing imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from dualexis.edge_perception.interfaces import PerceptionPipeline

if TYPE_CHECKING:
    from dualexis.schemas.audit import AuditEntry
    from dualexis.schemas.domain import FusedEvent, FusionResult, SafetyEvent
    from dualexis.schemas.fusion import FusionInput
    from dualexis.schemas.perception import PerceptionSignal
    from dualexis.schemas.privacy import PrivacyPolicy
    from dualexis.schemas.reasoning import ReasoningRequest, ReasoningResponse


class FusionEngine(ABC):
    """Fuses multimodal perception signals into unified semantic descriptors."""

    @abstractmethod
    async def fuse(self, inputs: FusionInput) -> FusionResult:
        """Combine signals from multiple modalities within a time window."""


class ReasoningEngine(ABC):
    """Performs local LLM reasoning over structured events only."""

    @abstractmethod
    async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        """Generate explainable decision support from structured event context."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the local reasoning backend is ready."""


class PrivacyGuard(ABC):
    """Enforces privacy policy constraints before data leaves the edge."""

    @abstractmethod
    def validate_signal(self, signal: PerceptionSignal) -> PerceptionSignal:
        """Strip or reject fields that violate the active privacy policy."""

    @abstractmethod
    def validate_event(self, event: SafetyEvent) -> SafetyEvent:
        """Ensure a safety event complies with privacy constraints."""

    @abstractmethod
    def active_policy(self) -> PrivacyPolicy:
        """Return the currently enforced privacy policy."""


class EventPublisher(ABC):
    """Publishes structured safety events to downstream consumers."""

    @abstractmethod
    async def publish(self, event: SafetyEvent | FusedEvent) -> str:
        """Publish an event and return its assigned identifier."""


class AuditLogger(ABC):
    """Append-only audit trail for explainability and compliance."""

    @abstractmethod
    async def log(self, entry: AuditEntry) -> None:
        """Record an audit entry."""

    @abstractmethod
    async def query(
        self,
        *,
        event_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters."""


__all__ = [
    "AuditLogger",
    "EventPublisher",
    "FusionEngine",
    "PerceptionPipeline",
    "PrivacyGuard",
    "ReasoningEngine",
]
