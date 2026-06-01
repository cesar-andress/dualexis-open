"""L4 Temporal Safety Graph Layer — service orchestration."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from dualexis.schemas.domain import SafetyEvent
from dualexis.semantic_events.models import SemanticEvent
from dualexis.temporal_graph.interfaces import TemporalGraphBackend, TemporalGraphService
from dualexis.temporal_graph.memory_backend import InMemoryTemporalGraphBackend
from dualexis.temporal_graph.models import (
    DEFAULT_CONTEXT_WINDOW,
    Exit,
    GraphContext,
    RiskState,
    Route,
    SemanticEventNode,
    Zone,
)


def semantic_event_node_from_safety(event: SafetyEvent) -> SemanticEventNode:
    """Map a legacy SafetyEvent to a graph semantic event node."""
    event_uuid = event.event_id if isinstance(event.event_id, UUID) else UUID(str(event.event_id))
    metadata = {str(key): str(value) for key, value in event.metadata.items()}
    category = event.descriptors[0].category if event.descriptors else "fused_event"
    metadata.setdefault("category", category)
    return SemanticEventNode(
        node_id=event_uuid,
        zone_id=event.zone_id,
        event_type=event.event_type.value,
        timestamp=event.timestamp,
        confidence=event.confidence.value,
        severity=event.severity.value,
        explanation=event.explanation,
        metadata=metadata,
    )


class InMemoryTemporalGraphService(TemporalGraphService):
    """Temporal safety graph service backed by the in-memory adapter."""

    def __init__(
        self,
        backend: TemporalGraphBackend | None = None,
        *,
        max_events: int = 1000,
    ) -> None:
        if backend is None:
            backend = InMemoryTemporalGraphBackend(max_events=max_events)
        self._backend = backend

    def add_zone(self, zone: Zone) -> None:
        self._backend.add_zone(zone)

    def add_exit(self, exit_node: Exit) -> None:
        self._backend.add_exit(exit_node)

    def add_route(self, route: Route) -> None:
        self._backend.add_route(route)

    def ingest_semantic_event(self, event: SemanticEvent) -> SemanticEventNode:
        node = SemanticEventNode.from_semantic_event(event)
        self._backend.ingest_event(node)
        return node

    def update_risk_state(self, state: RiskState) -> RiskState:
        self._backend.update_risk_state(state)
        return state

    def query_affected_routes(
        self,
        *,
        zone_id: str | None = None,
        exit_id: str | None = None,
    ) -> tuple[str, ...]:
        return self._backend.query_affected_routes(zone_id=zone_id, exit_id=exit_id)

    def get_reasoning_context(
        self,
        event_id: UUID,
        *,
        window: timedelta | None = None,
    ) -> GraphContext:
        return self._backend.build_context(
            event_id,
            window=window or DEFAULT_CONTEXT_WINDOW,
        )

    def add_event(self, event: SafetyEvent) -> None:
        self._backend.store_legacy_event(event)
        node = semantic_event_node_from_safety(event)
        self._backend.ingest_event(node)

    def link_events(self, source_id: UUID, target_id: UUID) -> None:
        self._backend.link_event_ids(source_id, target_id)

    def get_context(
        self,
        event_id: UUID,
        *,
        window: timedelta | None = None,
    ) -> tuple[SafetyEvent, ...]:
        return self._backend.get_legacy_context(
            event_id,
            window=window or DEFAULT_CONTEXT_WINDOW,
        )

    def size(self) -> int:
        return self._backend.event_count()


PlaceholderTemporalGraphService = InMemoryTemporalGraphService


__all__ = [
    "InMemoryTemporalGraphService",
    "PlaceholderTemporalGraphService",
    "semantic_event_node_from_safety",
]
