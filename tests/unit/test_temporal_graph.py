"""Unit tests for the Temporal Safety Graph abstraction."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel, is_forbidden_field
from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    EventType,
    LocationReference,
    SafetyEvent,
)
from dualexis.schemas.events import EventSeverity, SemanticDescriptor
from dualexis.semantic_events.models import EventSource as DomainEventSource
from dualexis.semantic_events.models import EventType as DomainEventType
from dualexis.semantic_events.models import SemanticEvent
from dualexis.temporal_graph import (
    Exit,
    GraphRelation,
    InMemoryTemporalGraphService,
    Neo4jTemporalGraphBackend,
    RiskState,
    Route,
    Zone,
)


def _now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _semantic_event(
    *,
    zone_id: str = "exit-c",
    event_type: DomainEventType = DomainEventType.EXIT_BLOCKAGE,
    metadata: dict[str, str] | None = None,
) -> SemanticEvent:
    return SemanticEvent(
        event_id=uuid4(),
        event_type=event_type,
        source=DomainEventSource.SIMULATOR,
        zone_id=zone_id,
        timestamp=_now(),
        confidence=0.82,
        severity=SeverityLevel.HIGH,
        explanation="Simulated exit blockage based on aggregate door and flow descriptors.",
        privacy_level=PrivacyLevel.SEMANTIC_ONLY,
        metadata=metadata or {"category": "exit_blocked"},
    )


def _safety_event(*, zone_id: str = "exit-c") -> SafetyEvent:
    return SafetyEvent(
        source=EventSource(node_id="edge-001", modality="sensor", pipeline_id="test"),
        location=LocationReference(zone_id=zone_id, zone_label=f"zone-{zone_id}"),
        event_type=EventType.ENVIRONMENTAL_SENSOR,
        severity=EventSeverity.HIGH,
        confidence=ConfidenceScore(value=0.8, rationale="Sensor obstruction score elevated."),
        explanation="Exit appears obstructed based on aggregate sensor descriptors.",
        timestamp=_now(),
        descriptors=(
            SemanticDescriptor(
                category="exit_blocked",
                description="Obstruction detected",
                confidence=0.8,
                source_modalities=("sensor",),
            ),
        ),
        metadata={"category": "exit_blocked"},
    )


def _build_graph() -> InMemoryTemporalGraphService:
    graph = InMemoryTemporalGraphService()
    graph.add_zone(Zone(zone_id="exit-c", label="Exit C", adjacent_zone_ids=("hall-a",)))
    graph.add_zone(Zone(zone_id="hall-a", label="Hall A"))
    graph.add_exit(Exit(exit_id="exit-c-main", zone_id="exit-c", label="Exit C Main"))
    graph.add_route(
        Route(
            route_id="evac-south",
            label="South Evacuation Route",
            zone_ids=("hall-a", "exit-c"),
            exit_ids=("exit-c-main",),
        )
    )
    return graph


@pytest.mark.unit
def test_graph_can_ingest_events() -> None:
    graph = _build_graph()
    event = _semantic_event()
    node = graph.ingest_semantic_event(event)
    assert graph.size() == 1
    assert node.zone_id == "exit-c"
    context = graph.get_reasoning_context(event.event_id)
    assert len(context.events) == 1
    assert context.events[0].node_id == event.event_id


@pytest.mark.unit
def test_exit_blockage_affects_route() -> None:
    graph = _build_graph()
    event = _semantic_event()
    graph.ingest_semantic_event(event)

    affected = graph.query_affected_routes(zone_id="exit-c")
    assert "evac-south" in affected

    reasoning = graph.get_reasoning_context(event.event_id)
    assert "evac-south" in reasoning.affected_route_ids
    assert any(edge.relation == GraphRelation.BLOCKS for edge in reasoning.edges)
    assert any(edge.relation == GraphRelation.AFFECTS for edge in reasoning.edges)


@pytest.mark.unit
def test_conflicting_events_are_represented() -> None:
    graph = _build_graph()
    baseline = _semantic_event(
        event_type=DomainEventType.NORMAL_FLOW,
        metadata={"category": "normal_flow"},
    )
    graph.ingest_semantic_event(baseline)

    conflict = _semantic_event(
        event_type=DomainEventType.MULTIMODAL_CONFLICT,
        metadata={"category": "multimodal_conflict"},
    )
    graph.ingest_semantic_event(conflict)

    context = graph.get_reasoning_context(conflict.event_id)
    assert any(edge.relation == GraphRelation.CONTRADICTS for edge in context.edges)


@pytest.mark.unit
def test_graph_context_contains_no_identity_fields() -> None:
    graph = _build_graph()
    event = _semantic_event()
    graph.ingest_semantic_event(event)
    graph.update_risk_state(
        RiskState(zone_id="exit-c", risk_score=0.7, updated_at=_now(), label="elevated")
    )

    context = graph.get_reasoning_context(event.event_id)
    payload = json.dumps(context.to_json_dict())

    forbidden_in_payload = [
        token
        for token in (
            "face_id",
            "person_id",
            "student_id",
            "biometric_hash",
            "voiceprint",
            "national_id",
            "raw_video_path",
        )
        if token in payload
    ]
    assert forbidden_in_payload == []

    def _walk_keys(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                assert not is_forbidden_field(str(key))
                _walk_keys(nested)
        elif isinstance(value, list):
            for item in value:
                _walk_keys(item)

    _walk_keys(context.to_json_dict())


@pytest.mark.unit
def test_graph_context_can_be_serialized_to_json() -> None:
    graph = _build_graph()
    event = _semantic_event()
    graph.ingest_semantic_event(event)
    context = graph.get_reasoning_context(event.event_id)
    serialized = json.dumps(context.to_json_dict())
    parsed = json.loads(serialized)
    assert parsed["anchor_event_id"] == str(event.event_id)
    assert parsed["events"]


@pytest.mark.unit
def test_legacy_add_event_api_still_works() -> None:
    graph = InMemoryTemporalGraphService()
    event = _safety_event()
    graph.add_event(event)
    assert graph.size() == 1
    assert graph.get_context(event.event_id) == ()


@pytest.mark.unit
def test_legacy_context_returns_zone_neighbors() -> None:
    graph = InMemoryTemporalGraphService()
    first = _safety_event(zone_id="hall-a")
    second = _safety_event(zone_id="hall-a")
    second = second.model_copy(update={"timestamp": _now() + timedelta(seconds=30)})
    graph.add_event(first)
    graph.add_event(second)
    context = graph.get_context(second.event_id)
    assert len(context) == 1
    assert context[0].event_id == first.event_id


@pytest.mark.unit
def test_neo4j_backend_is_placeholder() -> None:
    backend = Neo4jTemporalGraphBackend()
    with pytest.raises(NotImplementedError):
        backend.add_zone(Zone(zone_id="z1", label="Zone 1"))
