"""In-memory event graph for temporal and spatial event relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from uuid import UUID

from dualexis.schemas.domain import SafetyEvent


@dataclass
class EventGraphNode:
    """A node in the event graph representing a single safety event."""

    event: SafetyEvent
    related_event_ids: set[UUID] = field(default_factory=set)


class EventGraph:
    """Lightweight event graph for reasoning context assembly."""

    def __init__(self, max_nodes: int = 1000) -> None:
        self._nodes: dict[UUID, EventGraphNode] = {}
        self._max_nodes = max_nodes

    def add_event(self, event: SafetyEvent) -> None:
        event_uuid = (
            event.event_id if isinstance(event.event_id, UUID) else UUID(str(event.event_id))
        )
        self._nodes[event_uuid] = EventGraphNode(event=event)
        self._evict_if_needed()

    def link_events(self, source_id: UUID, target_id: UUID) -> None:
        if source_id in self._nodes and target_id in self._nodes:
            self._nodes[source_id].related_event_ids.add(target_id)
            self._nodes[target_id].related_event_ids.add(source_id)

    def get_context(
        self,
        event_id: UUID,
        *,
        window: timedelta = timedelta(minutes=5),
    ) -> list[SafetyEvent]:
        node = self._nodes.get(event_id)
        if node is None:
            return []

        cutoff = node.event.timestamp - window
        context: list[SafetyEvent] = []
        for other in self._nodes.values():
            if other.event.event_id == event_id:
                continue
            if other.event.zone_id == node.event.zone_id and other.event.timestamp >= cutoff:
                context.append(other.event)
        return sorted(context, key=lambda e: e.timestamp)

    def _evict_if_needed(self) -> None:
        if len(self._nodes) <= self._max_nodes:
            return
        oldest_id = min(self._nodes, key=lambda k: self._nodes[k].event.timestamp)
        del self._nodes[oldest_id]

    @property
    def size(self) -> int:
        return len(self._nodes)
