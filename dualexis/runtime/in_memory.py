"""Shared in-memory services and orchestrator factory for apps."""

from __future__ import annotations

from collections.abc import Mapping

from dualexis.audit.logger import InMemoryAuditLogger
from dualexis.core.interfaces import EventPublisher
from dualexis.edge_perception.interfaces import PerceptionPipeline
from dualexis.edge_perception.service import DefaultEdgePerceptionService
from dualexis.local_reasoning.service import PlaceholderLocalReasoningService
from dualexis.orchestration.service import SafetyOrchestrator
from dualexis.privacy_runtime.service import DefaultPrivacyRuntimeService
from dualexis.schemas.domain import FusedEvent, SafetyEvent
from dualexis.semantic_events.service import DefaultSemanticEventService
from dualexis.temporal_graph.service import InMemoryTemporalGraphService


class InMemoryEventPublisher(EventPublisher):
    """In-memory event publisher for development and testing."""

    def __init__(self) -> None:
        self._events: dict[str, SafetyEvent | FusedEvent] = {}

    async def publish(self, event: SafetyEvent | FusedEvent) -> str:
        event_id = str(event.event_id)
        self._events[event_id] = event
        return event_id

    def get(self, event_id: str) -> SafetyEvent | FusedEvent | None:
        return self._events.get(event_id)

    def list_events(self) -> list[SafetyEvent | FusedEvent]:
        return list(self._events.values())


def build_safety_orchestrator(
    node_id: str,
    pipelines: Mapping[str, PerceptionPipeline],
    *,
    publisher: InMemoryEventPublisher | None = None,
    audit_logger: InMemoryAuditLogger | None = None,
) -> SafetyOrchestrator:
    """Construct a framework-aligned SafetyOrchestrator (L1-L6)."""
    return SafetyOrchestrator(
        node_id=node_id,
        privacy_runtime=DefaultPrivacyRuntimeService(),
        edge_perception=DefaultEdgePerceptionService(pipelines),
        semantic_events=DefaultSemanticEventService(),
        temporal_graph=InMemoryTemporalGraphService(),
        local_reasoning=PlaceholderLocalReasoningService(),
        event_publisher=publisher or InMemoryEventPublisher(),
        audit_logger=audit_logger or InMemoryAuditLogger(),
    )
