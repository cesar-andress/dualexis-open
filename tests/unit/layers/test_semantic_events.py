"""Unit tests for L3 Semantic Event Layer."""

from __future__ import annotations

import pytest

from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    FusionResult,
    HumanReviewStatus,
    LocationReference,
)
from dualexis.schemas.events import EventSeverity
from dualexis.semantic_events import DefaultSemanticEventService


@pytest.mark.unit
def test_build_safety_event_includes_explanation() -> None:
    fusion = FusionResult(
        fusion_id="f-1",
        source=EventSource(node_id="edge-001", modality="multimodal", pipeline_id="t"),
        location=LocationReference(zone_id="z1", zone_label="Zone 1"),
        confidence=ConfidenceScore(value=0.7, rationale="Weighted fusion rationale."),
        fused_labels=("movement_detected",),
        explanation="Semantic fusion explanation text.",
        modality_contributions={"video": 0.7},
    )
    event = DefaultSemanticEventService().build_safety_event(
        fusion, node_id="edge-001", zone_id="z1"
    )
    assert event.explanation
    assert event.severity == EventSeverity.MEDIUM
    assert event.human_review == HumanReviewStatus.PENDING
