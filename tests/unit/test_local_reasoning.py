"""Unit tests for L5 local reasoning abstraction."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.local_reasoning import (
    AvailableProtocol,
    DefaultLocalReasoningService,
    LocalReasoningInput,
    MockLLMReasoner,
    SafetyConstraint,
    validate_reasoning_payload,
)
from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent
from dualexis.temporal_graph.models import GraphContext

ANCHOR_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
CONTEXT_ID = UUID("660e8400-e29b-41d4-a716-446655440001")
TIMESTAMP = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _semantic_event(
    *,
    event_id: UUID = ANCHOR_ID,
    severity: SeverityLevel = SeverityLevel.MEDIUM,
    event_type: EventType = EventType.EXIT_BLOCKAGE,
) -> SemanticEvent:
    return SemanticEvent(
        event_id=event_id,
        event_type=event_type,
        source=EventSource.SIMULATOR,
        zone_id="hallway-a",
        timestamp=TIMESTAMP,
        confidence=0.72,
        severity=severity,
        explanation="Structured semantic event only.",
        privacy_level=PrivacyLevel.SEMANTIC_ONLY,
    )


def _reasoning_input(
    *,
    severity: SeverityLevel = SeverityLevel.MEDIUM,
    include_context: bool = True,
) -> LocalReasoningInput:
    context: tuple[SemanticEvent, ...]
    if include_context:
        context = (_semantic_event(event_id=CONTEXT_ID, severity=SeverityLevel.LOW),)
    else:
        context = ()
    return LocalReasoningInput(
        request_id="req-local-001",
        anchor_event=_semantic_event(severity=severity),
        context_events=context,
        graph_context=GraphContext(
            anchor_event_id=ANCHOR_ID,
            affected_route_ids=("route-main",),
        ),
        safety_constraints=(
            SafetyConstraint(
                constraint_id="c1",
                description="Maintain egress clearance in hallway-a.",
            ),
        ),
        available_protocols=(
            AvailableProtocol(
                protocol_id="p1",
                protocol_name="Exit Clearance Protocol",
                description="Verify and clear blocked exits before resuming flow.",
            ),
        ),
    )


@pytest.mark.unit
def test_reasoner_rejects_raw_media() -> None:
    payload = {
        "anchor_event": _semantic_event().model_dump(mode="json"),
        "raw_video_path": "/tmp/camera-feed.mp4",
    }
    with pytest.raises(PrivacyViolationError, match="raw_video_path"):
        validate_reasoning_payload(payload)


@pytest.mark.unit
def test_reasoner_rejects_identities() -> None:
    payload = {
        "anchor_event": _semantic_event().model_dump(mode="json"),
        "metadata": {"person_id": "student-42"},
    }
    with pytest.raises(PrivacyViolationError, match="person_id"):
        validate_reasoning_payload(payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_high_risk_outputs_require_human_review() -> None:
    service = DefaultLocalReasoningService()
    for severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
        output = await service.reason_structured(_reasoning_input(severity=severity))
        assert output.required_human_review is True


@pytest.mark.unit
def test_mock_reasoner_produces_deterministic_output() -> None:
    reasoner = MockLLMReasoner()
    reasoning_input = _reasoning_input()
    first = reasoner.reason(reasoning_input)
    second = reasoner.reason(reasoning_input)
    assert first == second


@pytest.mark.unit
def test_recommendation_cites_source_events() -> None:
    reasoner = MockLLMReasoner()
    output = reasoner.reason(_reasoning_input())
    assert ANCHOR_ID in output.cited_event_ids
    assert CONTEXT_ID in output.cited_event_ids
    assert str(ANCHOR_ID) in output.rationale
