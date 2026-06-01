"""Tests for reasoning engine."""

from __future__ import annotations

import pytest

from dualexis.reasoning.engine import PlaceholderReasoningEngine
from dualexis.schemas.events import EventSeverity, SafetyEvent, SemanticDescriptor
from dualexis.schemas.reasoning import ReasoningRequest, RecommendedAction


def _make_event(severity: EventSeverity) -> SafetyEvent:
    return SafetyEvent(
        event_id="550e8400-e29b-41d4-a716-446655440000",
        node_id="edge-001",
        zone_id="hallway-a",
        severity=severity,
        descriptors=(
            SemanticDescriptor(
                category="multimodal_fusion",
                description="Test descriptor",
                confidence=0.75,
            ),
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reasoning_escalates_critical_events() -> None:
    engine = PlaceholderReasoningEngine()
    request = ReasoningRequest(
        request_id="req-001",
        event=_make_event(EventSeverity.CRITICAL),
    )
    response = await engine.reason(request)
    assert response.recommended_action == RecommendedAction.ESCALATE
    assert response.requires_human_review is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reasoning_no_action_for_info() -> None:
    engine = PlaceholderReasoningEngine()
    request = ReasoningRequest(
        request_id="req-002",
        event=_make_event(EventSeverity.INFO),
    )
    response = await engine.reason(request)
    assert response.recommended_action == RecommendedAction.NO_ACTION


@pytest.mark.unit
def test_reasoning_engine_is_available() -> None:
    engine = PlaceholderReasoningEngine()
    assert engine.is_available() is True
