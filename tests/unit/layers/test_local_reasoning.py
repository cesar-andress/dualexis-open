"""Unit tests for L5 Local Reasoning Layer."""

from __future__ import annotations

import pytest

from dualexis.local_reasoning import PlaceholderLocalReasoningService
from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    EventType,
    LocationReference,
    SafetyEvent,
)
from dualexis.schemas.events import EventSeverity, SemanticDescriptor
from dualexis.schemas.reasoning import ReasoningRequest


def _event() -> SafetyEvent:
    return SafetyEvent(
        source=EventSource(node_id="edge-001", modality="video", pipeline_id="t"),
        location=LocationReference(zone_id="z1", zone_label="Zone 1"),
        event_type=EventType.ZONE_ACTIVITY,
        severity=EventSeverity.MEDIUM,
        confidence=ConfidenceScore(value=0.7, rationale="Test rationale."),
        explanation="Structured event only.",
        descriptors=(
            SemanticDescriptor(
                category="zone_activity",
                description="activity",
                confidence=0.7,
                source_modalities=("video",),
            ),
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_placeholder_reasoning_returns_explanation() -> None:
    service = PlaceholderLocalReasoningService()
    request = ReasoningRequest(request_id="r1", event=_event())
    response = await service.reason(request)
    assert response.explanation
    assert response.requires_human_review is True
