"""Tests for core event and fusion schemas."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    EventType,
    FusedEvent,
    FusionResult,
    LocationReference,
    SafetyEvent,
)
from dualexis.schemas.events import EventSeverity, EventStatus, SemanticDescriptor


@pytest.mark.unit
def test_safety_event_validates_minimal_payload() -> None:
    event = SafetyEvent(
        source=EventSource(node_id="edge-001", modality="audio"),
        location=LocationReference(zone_id="hallway-a", zone_label="Hallway A"),
        event_type=EventType.ZONE_ACTIVITY,
        severity=EventSeverity.MEDIUM,
        confidence=ConfidenceScore(value=0.72, rationale="Moderate activity confidence"),
        explanation="Elevated noise level in zone",
        descriptors=(
            SemanticDescriptor(
                category="acoustic",
                description="Elevated noise level in zone",
                confidence=0.72,
                source_modalities=("audio",),
            ),
        ),
    )
    assert isinstance(event.event_id, UUID)
    assert event.status == EventStatus.DETECTED
    assert event.zone_id == "hallway-a"


@pytest.mark.unit
def test_safety_event_rejects_invalid_zone_id() -> None:
    with pytest.raises(ValidationError):
        SafetyEvent(
            source=EventSource(node_id="edge-001", modality="video"),
            location=LocationReference(zone_id="Invalid Zone", zone_label="Invalid"),
            event_type=EventType.UNKNOWN,
            severity=EventSeverity.LOW,
            confidence=ConfidenceScore(value=0.5, rationale="Test"),
            explanation="Invalid zone test",
            descriptors=(
                SemanticDescriptor(
                    category="test",
                    description="Test",
                    confidence=0.5,
                ),
            ),
        )


@pytest.mark.unit
def test_fused_event_extends_safety_event() -> None:
    fused = FusedEvent(
        source=EventSource(node_id="edge-001", modality="multimodal"),
        location=LocationReference(zone_id="cafeteria", zone_label="Cafeteria"),
        event_type=EventType.MULTIMODAL_FUSION,
        severity=EventSeverity.HIGH,
        confidence=ConfidenceScore(value=0.88, rationale="Strong multimodal agreement"),
        explanation="Fused activity in zone",
        descriptors=(
            SemanticDescriptor(
                category="multimodal_fusion",
                description="Fused activity in zone",
                confidence=0.88,
            ),
        ),
        fusion_score=0.88,
        contributing_signals=("sig-1", "sig-2"),
    )
    assert fused.status == EventStatus.FUSED
    assert fused.fusion_score == 0.88
    assert len(fused.contributing_signals) == 2


@pytest.mark.unit
def test_fusion_result_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        FusionResult(
            fusion_id="fusion-001",
            source=EventSource(node_id="edge-001", modality="multimodal"),
            location=LocationReference(zone_id="hallway-a", zone_label="Hallway A"),
            confidence=ConfidenceScore(value=1.5, rationale="Invalid"),
            fused_labels=("movement_detected",),
            explanation="Invalid confidence test",
        )
