"""Unit tests for the DUALEXIS domain model schemas."""

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
    HumanReviewStatus,
    LocationReference,
    NormalizedEvent,
    OrchestrationAction,
    OrchestrationRecommendation,
    PrivacyLevel,
    RetentionPolicy,
    SafetyEvent,
)
from dualexis.schemas.events import EventSeverity, SemanticDescriptor


def _confidence(value: float = 0.75) -> ConfidenceScore:
    return ConfidenceScore(value=value, rationale="Test confidence rationale")


def _source(modality: str = "video") -> EventSource:
    return EventSource(node_id="edge-001", modality=modality, pipeline_id="test-pipeline")


def _location(zone_id: str = "hallway-a") -> LocationReference:
    return LocationReference(zone_id=zone_id, zone_label="Hallway A")


def _descriptor() -> SemanticDescriptor:
    return SemanticDescriptor(
        category="zone_activity",
        description="Moderate activity detected in zone",
        confidence=0.72,
        source_modalities=("video",),
    )


@pytest.mark.unit
class TestConfidenceScore:
    def test_validates_range_and_rationale(self) -> None:
        score = _confidence(0.5)
        assert score.value == 0.5
        assert score.rationale

    def test_rejects_missing_rationale(self) -> None:
        with pytest.raises(ValidationError):
            ConfidenceScore(value=0.5, rationale="")

    def test_rejects_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            ConfidenceScore(value=1.5, rationale="Invalid score")


@pytest.mark.unit
class TestLocationReference:
    def test_validates_zone_reference(self) -> None:
        location = _location()
        assert location.zone_id == "hallway-a"
        assert location.site_id is None

    def test_rejects_identity_terms_in_label(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            LocationReference(zone_id="hallway-a", zone_label="student desk area")


@pytest.mark.unit
class TestEventSource:
    def test_validates_provenance(self) -> None:
        source = _source("audio")
        assert source.node_id == "edge-001"
        assert source.modality == "audio"

    def test_rejects_biometric_pipeline_id(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            EventSource(node_id="edge-001", modality="video", pipeline_id="face-detector")


@pytest.mark.unit
class TestDomainEnums:
    def test_event_type_values(self) -> None:
        assert EventType.MULTIMODAL_FUSION.value == "multimodal_fusion"

    def test_privacy_level_values(self) -> None:
        assert PrivacyLevel.EPHEMERAL.value == "ephemeral"

    def test_retention_policy_values(self) -> None:
        assert RetentionPolicy.STANDARD.value == "standard"

    def test_human_review_status_values(self) -> None:
        assert HumanReviewStatus.PENDING.value == "pending"


@pytest.mark.unit
class TestNormalizedEvent:
    def test_validates_normalized_event(self) -> None:
        event = NormalizedEvent(
            source=_source(),
            location=_location(),
            event_type=EventType.ZONE_ACTIVITY,
            confidence=_confidence(),
            labels=("movement_detected",),
            explanation="Zone-level movement detected without identity features",
        )
        assert isinstance(event.event_id, UUID)
        assert event.privacy_level == PrivacyLevel.EPHEMERAL
        assert event.retention == RetentionPolicy.EPHEMERAL

    def test_rejects_identity_labels(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            NormalizedEvent(
                source=_source(),
                location=_location(),
                event_type=EventType.UNKNOWN,
                confidence=_confidence(),
                labels=("student_identified",),
                explanation="Invalid label set",
            )


@pytest.mark.unit
class TestFusionResult:
    def test_validates_fusion_result(self) -> None:
        result = FusionResult(
            fusion_id="fusion-001",
            source=_source("multimodal"),
            location=_location(),
            confidence=_confidence(0.8),
            fused_labels=("movement_detected", "elevated_noise_level"),
            explanation="Fusion combined video and audio normalized signals",
            signal_ids=("sig-1", "sig-2"),
            modality_contributions={"video": 0.32, "audio": 0.28},
        )
        assert result.fused_confidence == 0.8
        assert result.node_id == "edge-001"
        assert result.zone_id == "hallway-a"

    def test_rejects_empty_fused_labels(self) -> None:
        with pytest.raises(ValidationError):
            FusionResult(
                fusion_id="fusion-002",
                source=_source("multimodal"),
                location=_location(),
                confidence=_confidence(),
                fused_labels=(),
                explanation="Missing labels",
            )


@pytest.mark.unit
class TestOrchestrationRecommendation:
    def test_validates_recommendation_with_explanation(self) -> None:
        recommendation = OrchestrationRecommendation(
            action=OrchestrationAction.REQUEST_REVIEW,
            confidence=_confidence(0.66),
            explanation="Elevated multimodal risk warrants staff review",
            requires_human_approval=True,
        )
        assert recommendation.action == OrchestrationAction.REQUEST_REVIEW
        assert recommendation.requires_human_approval is True


@pytest.mark.unit
class TestSafetyEvent:
    def test_validates_full_safety_event(self) -> None:
        event = SafetyEvent(
            source=_source(),
            location=_location(),
            event_type=EventType.MULTIMODAL_FUSION,
            severity=EventSeverity.MEDIUM,
            confidence=_confidence(),
            explanation="Structured safety event for staff review",
            human_review=HumanReviewStatus.PENDING,
            descriptors=(_descriptor(),),
        )
        assert event.requires_human_review is True
        assert event.node_id == "edge-001"
        assert event.zone_id == "hallway-a"

    def test_legacy_flat_field_coercion(self) -> None:
        event = SafetyEvent(
            node_id="edge-legacy",
            zone_id="cafeteria",
            severity=EventSeverity.LOW,
            descriptors=(_descriptor(),),
            requires_human_review=False,
        )
        assert event.source.node_id == "edge-legacy"
        assert event.location.zone_id == "cafeteria"
        assert event.explanation

    def test_fused_event_extends_safety_event(self) -> None:
        fused = FusedEvent(
            source=_source("multimodal"),
            location=_location(),
            event_type=EventType.MULTIMODAL_FUSION,
            severity=EventSeverity.HIGH,
            confidence=_confidence(0.9),
            explanation="Fused multimodal safety event",
            descriptors=(_descriptor(),),
            fusion_score=0.9,
            contributing_signals=("sig-a", "sig-b"),
            human_review=HumanReviewStatus.PENDING,
        )
        assert fused.fusion_score == fused.confidence.value
        assert len(fused.contributing_signals) == 2


@pytest.mark.unit
class TestRetentionPolicyIntegration:
    def test_safety_event_retention_default(self) -> None:
        event = SafetyEvent(
            source=_source(),
            location=_location(),
            event_type=EventType.ENVIRONMENTAL_SENSOR,
            severity=EventSeverity.INFO,
            confidence=_confidence(0.4),
            explanation="Environmental sensor event",
            retention=RetentionPolicy.SHORT,
            descriptors=(_descriptor(),),
        )
        assert event.retention == RetentionPolicy.SHORT
        assert event.privacy_level == PrivacyLevel.INTERNAL
