"""L5 Local Reasoning Layer — service implementation."""

from __future__ import annotations

from uuid import UUID

from dualexis.local_reasoning.interfaces import LocalReasoningService, Reasoner
from dualexis.local_reasoning.mock_llm import MockLLMReasoner
from dualexis.local_reasoning.models import (
    CopilotConfig,
    LocalReasoningInput,
    LocalReasoningOutput,
    ReasoningRequest,
    ReasoningResponse,
    validate_reasoning_payload,
)
from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel as DomainPrivacyLevel
from dualexis.schemas.domain import SafetyEvent
from dualexis.schemas.events import EventSeverity
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent

_SCHEMA_TO_DOMAIN_EVENT_TYPE: dict[str, EventType] = {
    "zone_activity": EventType.NORMAL_FLOW,
    "crowd_density": EventType.CROWD_ACCELERATION,
    "exit_blockage": EventType.EXIT_BLOCKAGE,
    "audio_stress": EventType.AUDIO_STRESS_SIGNAL,
    "fall_detected": EventType.FALL_DETECTED,
    "multimodal_conflict": EventType.MULTIMODAL_CONFLICT,
    "evacuation_signal": EventType.EVACUATION_SIGNAL,
}

_SEVERITY_TO_DOMAIN: dict[EventSeverity, SeverityLevel] = {
    EventSeverity.INFO: SeverityLevel.LOW,
    EventSeverity.LOW: SeverityLevel.LOW,
    EventSeverity.MEDIUM: SeverityLevel.MEDIUM,
    EventSeverity.HIGH: SeverityLevel.HIGH,
    EventSeverity.CRITICAL: SeverityLevel.CRITICAL,
}

_SCHEMA_PRIVACY_TO_DOMAIN: dict[str, DomainPrivacyLevel] = {
    "ephemeral": DomainPrivacyLevel.EPHEMERAL,
    "internal": DomainPrivacyLevel.SEMANTIC_ONLY,
    "restricted": DomainPrivacyLevel.AGGREGATED,
    "public": DomainPrivacyLevel.AUDIT_ONLY,
}


def semantic_event_from_safety(event: SafetyEvent) -> SemanticEvent:
    """Map a legacy SafetyEvent to the canonical SemanticEvent domain model."""
    schema_type = event.event_type.value
    domain_type = _SCHEMA_TO_DOMAIN_EVENT_TYPE.get(schema_type, EventType.UNKNOWN)
    severity = _SEVERITY_TO_DOMAIN.get(event.severity, SeverityLevel.MEDIUM)

    category = event.descriptors[0].category if event.descriptors else "fused_event"
    modalities = (
        ",".join(event.descriptors[0].source_modalities)
        if event.descriptors and event.descriptors[0].source_modalities
        else "video,audio,sensor"
    )

    event_uuid = event.event_id if isinstance(event.event_id, UUID) else UUID(str(event.event_id))

    return SemanticEvent(
        event_id=event_uuid,
        event_type=domain_type,
        source=EventSource.SIMULATOR,
        zone_id=event.zone_id,
        timestamp=event.timestamp,
        confidence=event.confidence.value,
        severity=severity,
        explanation=event.explanation,
        privacy_level=_SCHEMA_PRIVACY_TO_DOMAIN.get(
            event.privacy_level.value,
            DomainPrivacyLevel.SEMANTIC_ONLY,
        ),
        metadata={
            "category": category,
            "modalities": modalities,
            "legacy_severity": event.severity.value,
        },
    )


def reasoning_input_from_request(request: ReasoningRequest) -> LocalReasoningInput:
    """Convert a legacy ``ReasoningRequest`` into structured L5 input."""
    anchor = semantic_event_from_safety(request.event)
    context = tuple(semantic_event_from_safety(event) for event in request.context_events)
    return LocalReasoningInput(
        request_id=request.request_id,
        anchor_event=anchor,
        context_events=context,
    )


def reasoning_response_from_output(
    output: LocalReasoningOutput,
    *,
    anchor_event_id: UUID,
) -> ReasoningResponse:
    """Map structured L5 output to the legacy ``ReasoningResponse`` schema."""
    return ReasoningResponse(
        request_id=output.request_id,
        event_id=anchor_event_id,
        summary=output.recommendation,
        explanation=output.rationale,
        confidence=output.confidence_band,
        recommended_action=output.recommended_action,
        requires_human_review=output.required_human_review,
        model_id=output.model_id,
    )


class DefaultLocalReasoningService(LocalReasoningService):
    """Local reasoning service backed by a structured-event reasoner."""

    def __init__(
        self,
        config: CopilotConfig | None = None,
        *,
        reasoner: Reasoner | None = None,
    ) -> None:
        self._config = config or CopilotConfig()
        self._reasoner = reasoner or MockLLMReasoner(model_id=self._config.model_id)

    async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        reasoning_input = reasoning_input_from_request(request)
        output = await self.reason_structured(reasoning_input)
        anchor_id = reasoning_input.anchor_event.event_id
        return reasoning_response_from_output(output, anchor_event_id=anchor_id)

    async def reason_structured(
        self,
        reasoning_input: LocalReasoningInput,
    ) -> LocalReasoningOutput:
        validate_reasoning_payload(reasoning_input.model_dump(mode="json"))
        if self._config.allow_raw_media_prompts:
            msg = "Raw media prompts are disabled by default in DUALEXIS local reasoning"
            raise ValueError(msg)
        return self._reasoner.reason(reasoning_input)

    def is_available(self) -> bool:
        return True

    @property
    def config(self) -> CopilotConfig:
        return self._config

    @property
    def reasoner(self) -> Reasoner:
        return self._reasoner


class PlaceholderLocalReasoningService(DefaultLocalReasoningService):
    """Backward-compatible alias for the deterministic mock reasoner service."""


__all__ = [
    "DefaultLocalReasoningService",
    "PlaceholderLocalReasoningService",
    "reasoning_input_from_request",
    "reasoning_response_from_output",
    "semantic_event_from_safety",
]
