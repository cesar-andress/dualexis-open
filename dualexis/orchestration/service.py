"""L6 Human-in-the-Loop Orchestration Layer — framework-aligned pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from dualexis.core.interfaces import AuditLogger, EventPublisher
from dualexis.edge_perception.interfaces import EdgePerceptionService
from dualexis.local_reasoning.interfaces import LocalReasoningService
from dualexis.local_reasoning.models import ReasoningRequest, ReasoningResponse
from dualexis.orchestration.interfaces import OrchestrationService
from dualexis.orchestration.models import HIGH_RISK_SEVERITIES
from dualexis.privacy_runtime.interfaces import PrivacyRuntimeService
from dualexis.privacy_runtime.models import TrustBoundary
from dualexis.schemas.audit import AuditAction, AuditEntry
from dualexis.schemas.domain import (
    HumanReviewStatus,
    OrchestrationAction,
    OrchestrationRecommendation,
    SafetyEvent,
)
from dualexis.schemas.events import EventStatus
from dualexis.schemas.fusion import FusionInput
from dualexis.schemas.perception import PerceptionFrame
from dualexis.semantic_events.interfaces import SemanticEventService
from dualexis.temporal_graph.interfaces import TemporalGraphService


class SafetyOrchestrator(OrchestrationService):
    """Composes L1-L5 services into an advisory human-in-the-loop pipeline."""

    def __init__(
        self,
        *,
        node_id: str,
        privacy_runtime: PrivacyRuntimeService,
        edge_perception: EdgePerceptionService,
        semantic_events: SemanticEventService,
        temporal_graph: TemporalGraphService,
        local_reasoning: LocalReasoningService,
        event_publisher: EventPublisher,
        audit_logger: AuditLogger,
    ) -> None:
        self._node_id = node_id
        self._privacy = privacy_runtime
        self._perception = edge_perception
        self._events = semantic_events
        self._graph = temporal_graph
        self._reasoning = local_reasoning
        self._publisher = event_publisher
        self._audit = audit_logger

    async def process_frames(
        self,
        frames: list[PerceptionFrame],
        *,
        zone_id: str,
    ) -> SafetyEvent:
        for frame in frames:
            self._privacy.validate_frame(frame)

        raw_signals = await self._perception.process_frames(frames)
        validated_signals = []
        for signal in raw_signals:
            validated = self._privacy.validate_signal(signal)
            validated_signals.append(validated)
            await self._audit.log(
                AuditEntry(
                    entry_id=str(uuid4()),
                    action=AuditAction.PERCEPTION_PROCESSED,
                    node_id=self._node_id,
                    details={
                        "signal_id": validated.signal_id,
                        "modality": validated.modality.value,
                    },
                )
            )

        now = datetime.now(tz=UTC)
        fusion_input = FusionInput(
            node_id=self._node_id,
            zone_id=zone_id,
            window_start=now - timedelta(seconds=5),
            window_end=now,
            signals=tuple(validated_signals),
        )
        fusion_result = await self._events.fuse_signals(fusion_input)
        await self._audit.log(
            AuditEntry(
                entry_id=str(uuid4()),
                action=AuditAction.FUSION_COMPLETED,
                node_id=self._node_id,
                details={"fusion_id": fusion_result.fusion_id},
            )
        )

        safety_event = self._events.build_safety_event(
            fusion_result,
            node_id=self._node_id,
            zone_id=zone_id,
        )
        validated_event = self._privacy.validate_event(safety_event)
        self._graph.add_event(validated_event)

        if self._reasoning.is_available():
            event_uuid = self._event_uuid(validated_event)
            context = self._graph.get_context(event_uuid)
            reasoning_request = ReasoningRequest(
                request_id=str(uuid4()),
                event=validated_event,
                context_events=context,
            )
            self._privacy.check_egress(
                {"event_id": str(validated_event.event_id)},
                boundary=TrustBoundary.TB4_LLM_REASONING,
            )
            reasoning_response = await self._reasoning.reason(reasoning_request)
            recommendation = OrchestrationRecommendation(
                action=OrchestrationAction(reasoning_response.recommended_action.value),
                confidence=validated_event.confidence,
                explanation=reasoning_response.explanation,
                requires_human_approval=self._requires_human_review(
                    validated_event, reasoning_response
                ),
            )
            validated_event = validated_event.model_copy(
                update={
                    "status": EventStatus.REASONED,
                    "recommendation": recommendation,
                    "human_review": (
                        HumanReviewStatus.PENDING
                        if recommendation.requires_human_approval
                        else HumanReviewStatus.NOT_REQUIRED
                    ),
                }
            )
            await self._audit.log(
                AuditEntry(
                    entry_id=str(uuid4()),
                    action=AuditAction.REASONING_INVOKED,
                    node_id=self._node_id,
                    event_id=event_uuid,
                    details={"recommended_action": reasoning_response.recommended_action.value},
                )
            )

        self._privacy.check_egress(
            validated_event.model_dump(mode="json"),
            boundary=TrustBoundary.TB5_NETWORK_EGRESS,
        )
        published_id = await self._publisher.publish(validated_event)
        await self._audit.log(
            AuditEntry(
                entry_id=str(uuid4()),
                action=AuditAction.EVENT_PUBLISHED,
                node_id=self._node_id,
                details={"published_event_id": published_id},
            )
        )
        return validated_event

    @staticmethod
    def _event_uuid(event: SafetyEvent) -> UUID:
        return event.event_id if isinstance(event.event_id, UUID) else UUID(str(event.event_id))

    @staticmethod
    def _requires_human_review(event: SafetyEvent, response: ReasoningResponse) -> bool:
        if event.severity.value in HIGH_RISK_SEVERITIES:
            return True
        return response.requires_human_review
