"""Tests for event graph."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from dualexis.graph.event_graph import EventGraph
from dualexis.schemas.events import EventSeverity, SafetyEvent, SemanticDescriptor


def _make_event(zone_id: str, offset_seconds: int = 0) -> SafetyEvent:
    return SafetyEvent(
        event_id=uuid4(),
        node_id="edge-001",
        zone_id=zone_id,
        timestamp=datetime.now(tz=UTC) - timedelta(seconds=offset_seconds),
        severity=EventSeverity.LOW,
        descriptors=(SemanticDescriptor(category="test", description="Test", confidence=0.5),),
    )


@pytest.mark.unit
def test_event_graph_stores_and_links_events() -> None:
    graph = EventGraph()
    event_a = _make_event("hallway-a")
    event_b = _make_event("hallway-a", offset_seconds=10)
    graph.add_event(event_a)
    graph.add_event(event_b)
    assert graph.size == 2


@pytest.mark.unit
def test_event_graph_returns_zone_context() -> None:
    graph = EventGraph()
    event_a = _make_event("hallway-a")
    event_b = _make_event("hallway-a", offset_seconds=30)
    event_c = _make_event("cafeteria")
    graph.add_event(event_a)
    graph.add_event(event_b)
    graph.add_event(event_c)

    from uuid import UUID

    event_uuid = (
        event_a.event_id if isinstance(event_a.event_id, UUID) else UUID(str(event_a.event_id))
    )
    context = graph.get_context(event_uuid, window=timedelta(minutes=5))
    zone_ids = {e.zone_id for e in context}
    assert zone_ids == {"hallway-a"}
