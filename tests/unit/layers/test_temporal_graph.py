"""Unit tests for L4 Temporal Safety Graph Layer."""

from __future__ import annotations

import pytest

from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    EventType,
    LocationReference,
    SafetyEvent,
)
from dualexis.schemas.events import EventSeverity, SemanticDescriptor
from dualexis.temporal_graph import InMemoryTemporalGraphService


def _event(zone_id: str = "z1") -> SafetyEvent:
    return SafetyEvent(
        source=EventSource(node_id="edge-001", modality="video", pipeline_id="t"),
        location=LocationReference(zone_id=zone_id, zone_label=f"zone-{zone_id}"),
        event_type=EventType.ZONE_ACTIVITY,
        severity=EventSeverity.LOW,
        confidence=ConfidenceScore(value=0.5, rationale="Test rationale."),
        explanation="Test event.",
        descriptors=(
            SemanticDescriptor(
                category="zone_activity",
                description="activity",
                confidence=0.5,
                source_modalities=("video",),
            ),
        ),
    )


@pytest.mark.unit
def test_graph_stores_and_returns_context() -> None:
    graph = InMemoryTemporalGraphService()
    event = _event()
    graph.add_event(event)
    context = graph.get_context(event.event_id)
    assert graph.size() == 1
    assert context == ()
