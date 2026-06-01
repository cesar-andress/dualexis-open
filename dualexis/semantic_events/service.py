"""L3 Semantic Event Layer — default service implementation."""

from __future__ import annotations

from uuid import uuid4

from dualexis.fusion.engine import DefaultFusionEngine
from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    EventType,
    FusedEvent,
    FusionResult,
    HumanReviewStatus,
    LocationReference,
    SafetyEvent,
)
from dualexis.schemas.events import EventSeverity, SemanticDescriptor
from dualexis.schemas.fusion import FusionInput
from dualexis.semantic_events.interfaces import SemanticEventService


class DefaultSemanticEventService(SemanticEventService):
    """Placeholder semantic event service wrapping the default fusion engine."""

    def __init__(self) -> None:
        self._fusion = DefaultFusionEngine()

    async def fuse_signals(self, fusion_input: FusionInput) -> FusionResult:
        return await self._fusion.fuse(fusion_input)

    def build_safety_event(
        self,
        fusion_result: FusionResult,
        *,
        node_id: str,
        zone_id: str,
    ) -> SafetyEvent:
        severity = self._infer_severity(fusion_result.fused_confidence)
        review_status = (
            HumanReviewStatus.PENDING
            if severity in {EventSeverity.MEDIUM, EventSeverity.HIGH, EventSeverity.CRITICAL}
            else HumanReviewStatus.NOT_REQUIRED
        )
        descriptor = SemanticDescriptor(
            category="multimodal_fusion",
            description=f"Fused labels: {', '.join(fusion_result.fused_labels)}",
            confidence=fusion_result.fused_confidence,
            source_modalities=tuple(fusion_result.modality_contributions.keys()),
        )
        return FusedEvent(
            event_id=uuid4(),
            source=EventSource(
                node_id=node_id,
                modality="multimodal",
                pipeline_id="semantic-event-service",
            ),
            location=LocationReference(zone_id=zone_id, zone_label=f"zone-{zone_id}"),
            event_type=EventType.MULTIMODAL_FUSION,
            severity=severity,
            confidence=ConfidenceScore(
                value=fusion_result.fused_confidence,
                rationale=fusion_result.confidence.rationale,
            ),
            explanation=fusion_result.explanation,
            human_review=review_status,
            descriptors=(descriptor,),
            fusion_score=fusion_result.fused_confidence,
            contributing_signals=fusion_result.signal_ids,
        )

    @staticmethod
    def _infer_severity(confidence: float) -> EventSeverity:
        if confidence >= 0.85:
            return EventSeverity.HIGH
        if confidence >= 0.65:
            return EventSeverity.MEDIUM
        if confidence >= 0.4:
            return EventSeverity.LOW
        return EventSeverity.INFO


PlaceholderSemanticEventService = DefaultSemanticEventService
