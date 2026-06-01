"""Framework constraint tests — privacy and orchestration invariants."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.orchestration.models import HIGH_RISK_SEVERITIES
from dualexis.privacy_runtime import DefaultPrivacyRuntimeService
from dualexis.privacy_runtime.models import FORBIDDEN_BIOMETRIC_KEYS, FORBIDDEN_IDENTITY_TERMS
from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    EventType,
    HumanReviewStatus,
    LocationReference,
    OrchestrationAction,
    OrchestrationRecommendation,
    SafetyEvent,
)
from dualexis.schemas.events import EventSeverity, SemanticDescriptor
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal, ZoneDescriptor
from dualexis.schemas.reasoning import ReasoningRequest, ReasoningResponse


def _confidence(value: float = 0.75) -> ConfidenceScore:
    return ConfidenceScore(value=value, rationale="Derived from zone-level descriptors.")


def _safety_event(*, severity: EventSeverity = EventSeverity.MEDIUM) -> SafetyEvent:
    return SafetyEvent(
        source=EventSource(node_id="edge-001", modality="video", pipeline_id="test"),
        location=LocationReference(zone_id="hall-a", zone_label="Hall A"),
        event_type=EventType.ZONE_ACTIVITY,
        severity=severity,
        confidence=_confidence(),
        explanation="Zone activity elevated without identity attribution.",
        descriptors=(
            SemanticDescriptor(
                category="zone_activity",
                description="Activity band increased",
                confidence=0.7,
                source_modalities=("video",),
            ),
        ),
    )


@pytest.mark.unit
class TestNoBiometricSchemaFields:
    """Prove framework schemas do not define biometric field names."""

    @pytest.mark.parametrize("model_cls", [PerceptionSignal, SafetyEvent, ReasoningRequest])
    def test_model_fields_exclude_biometric_names(self, model_cls: type[BaseModel]) -> None:
        field_names = {name.lower() for name in model_cls.model_fields}
        for forbidden in FORBIDDEN_BIOMETRIC_KEYS:
            assert forbidden not in field_names
        assert "biometric" not in field_names
        assert "face_embedding" not in field_names

    def test_runtime_rejects_biometric_feature_keys(self) -> None:
        zone = ZoneDescriptor(
            zone_id="z1",
            label="zone-z1",
            occupancy_estimate=5,
            activity_level=0.3,
        )
        signal = PerceptionSignal(
            modality=Modality.VIDEO,
            node_id="edge-001",
            zone=zone,
            confidence=0.5,
            features={"face_embedding": 0.99},
        )
        with pytest.raises(PrivacyViolationError):
            DefaultPrivacyRuntimeService().validate_signal(signal)


@pytest.mark.unit
class TestNoPersonalIdentityRequired:
    """Prove schemas do not require personal identity fields."""

    @pytest.mark.parametrize(
        "model_cls",
        [PerceptionFrame, PerceptionSignal, SafetyEvent, ReasoningRequest],
    )
    def test_no_identity_named_required_fields(self, model_cls: type[BaseModel]) -> None:
        for name, field in model_cls.model_fields.items():
            lowered = name.lower()
            if any(term in lowered for term in FORBIDDEN_IDENTITY_TERMS):
                assert not field.is_required(), f"{model_cls.__name__}.{name} must not be required"

    def test_safety_event_without_identity_metadata(self) -> None:
        event = _safety_event()
        assert "person_id" not in event.metadata
        assert event.location.zone_id == "hall-a"


@pytest.mark.unit
class TestSemanticEventsWithoutRawMedia:
    """Prove semantic events can be created without raw media storage."""

    def test_safety_event_has_no_media_payload_fields(self) -> None:
        event = _safety_event()
        dumped = event.model_dump()
        assert "raw_video" not in dumped
        assert "raw_audio" not in dumped
        assert "payload_ref" not in dumped

    def test_perception_frame_payload_ref_optional(self) -> None:
        frame = PerceptionFrame(modality="video", node_id="edge-001", zone_id="hall-a")
        assert frame.payload_ref is None

    def test_descriptor_evidence_rejects_raw_media(self) -> None:
        with pytest.raises(ValidationError):
            SemanticDescriptor(
                category="zone_activity",
                description="Invalid evidence",
                confidence=0.5,
                evidence={"raw_video": "path/to/file"},
            )


@pytest.mark.unit
class TestOrchestrationRecommendationsIncludeExplanations:
    """Prove orchestration recommendations require explanations."""

    def test_recommendation_requires_explanation(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationRecommendation(
                action=OrchestrationAction.MONITOR,
                confidence=_confidence(),
                explanation="",
            )

    def test_recommendation_with_explanation(self) -> None:
        rec = OrchestrationRecommendation(
            action=OrchestrationAction.REQUEST_REVIEW,
            confidence=_confidence(),
            explanation="Correlated zone events warrant staff review.",
        )
        assert rec.explanation
        assert rec.requires_human_approval is True


@pytest.mark.unit
class TestHumanReviewMandatoryForHighRisk:
    """Prove high-risk severities require human review in orchestration layer."""

    @pytest.mark.parametrize("severity", [EventSeverity.HIGH, EventSeverity.CRITICAL])
    def test_high_risk_severity_in_set(self, severity: EventSeverity) -> None:
        assert severity.value in HIGH_RISK_SEVERITIES

    def test_orchestrator_forces_review_for_high_severity(self) -> None:
        from dualexis.orchestration.service import SafetyOrchestrator
        from dualexis.schemas.reasoning import ReasoningConfidence, RecommendedAction

        event = _safety_event(severity=EventSeverity.HIGH)
        response = ReasoningResponse(
            request_id="req-1",
            event_id=event.event_id,
            summary="High severity zone event.",
            explanation="Elevated confidence across modalities.",
            confidence=ReasoningConfidence.MEDIUM,
            recommended_action=RecommendedAction.MONITOR,
            requires_human_review=False,
        )
        assert SafetyOrchestrator._requires_human_review(event, response) is True

    def test_build_safety_event_sets_pending_for_medium_plus(self) -> None:
        from dualexis.schemas.domain import FusionResult
        from dualexis.semantic_events.service import DefaultSemanticEventService

        fusion = FusionResult(
            fusion_id="f-1",
            source=EventSource(node_id="edge-001", modality="multimodal", pipeline_id="test"),
            location=LocationReference(zone_id="hall-a", zone_label="Hall A"),
            confidence=_confidence(0.9),
            fused_labels=("elevated_activity",),
            explanation="Fusion produced high confidence labels.",
            modality_contributions={"video": 0.9},
        )
        event = DefaultSemanticEventService().build_safety_event(
            fusion, node_id="edge-001", zone_id="hall-a"
        )
        assert event.human_review == HumanReviewStatus.PENDING
