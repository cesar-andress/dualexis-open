"""Unit tests for core Pydantic v2 layer domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from dualexis.orchestration.models import (
    HIGH_RISK_SEVERITIES,
    HumanReviewStatus,
    OrchestrationRecommendation,
    SeverityLevel,
)
from dualexis.privacy_runtime.models import (
    DEFAULT_RETENTION_POLICY,
    PrivacyLevel,
    RetentionPolicy,
)
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent
from dualexis.temporal_graph.models import (
    TemporalEdgeKind,
    TemporalGraphEdge,
    TemporalGraphNode,
)


def _now() -> datetime:
    return datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)


def _semantic_event(**overrides: object) -> SemanticEvent:
    defaults: dict[str, object] = {
        "event_id": uuid4(),
        "event_type": EventType.CROWD_ACCELERATION,
        "source": EventSource.VIDEO_EDGE_NODE,
        "zone_id": "hall-a",
        "timestamp": _now(),
        "confidence": 0.82,
        "severity": SeverityLevel.MEDIUM,
        "explanation": "Crowd density increased in zone based on aggregate motion descriptors.",
        "privacy_level": PrivacyLevel.SEMANTIC_ONLY,
    }
    defaults.update(overrides)
    return SemanticEvent(**defaults)


def _recommendation(**overrides: object) -> OrchestrationRecommendation:
    defaults: dict[str, object] = {
        "recommendation_id": uuid4(),
        "based_on_events": [uuid4()],
        "target_zone_id": "exit-c",
        "action": "Direct staff to verify exit clearance",
        "rationale": "Correlated exit blockage signals across adjacent zones.",
        "severity": SeverityLevel.MEDIUM,
        "requires_human_review": False,
        "human_review_status": HumanReviewStatus.NOT_REQUIRED,
        "created_at": _now(),
    }
    defaults.update(overrides)
    return OrchestrationRecommendation(**defaults)


@pytest.mark.unit
class TestSemanticEvent:
    def test_valid_semantic_event(self) -> None:
        event = _semantic_event()
        assert event.event_type == EventType.CROWD_ACCELERATION
        assert event.source == EventSource.VIDEO_EDGE_NODE
        assert event.raw_media_persisted is False
        assert event.metadata == {}

    @pytest.mark.parametrize(
        "confidence",
        [-0.01, 1.01],
    )
    def test_confidence_bounds(self, confidence: float) -> None:
        with pytest.raises(ValidationError):
            _semantic_event(confidence=confidence)

    def test_rejects_identity_terms_in_zone_id(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            _semantic_event(zone_id="student-wing-a")

    def test_rejects_forbidden_metadata_keys(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            _semantic_event(metadata={"face_score": "0.9"})

    def test_rejects_raw_media_persisted_true(self) -> None:
        with pytest.raises(ValidationError, match="raw_media_persisted"):
            _semantic_event(raw_media_persisted=True)

    @pytest.mark.parametrize("event_type", list(EventType))
    def test_all_event_types_accepted(self, event_type: EventType) -> None:
        event = _semantic_event(event_type=event_type)
        assert event.event_type == event_type

    @pytest.mark.parametrize("source", list(EventSource))
    def test_all_event_sources_accepted(self, source: EventSource) -> None:
        event = _semantic_event(source=source)
        assert event.source == source


@pytest.mark.unit
class TestRetentionPolicy:
    def test_default_policy_is_privacy_first(self) -> None:
        policy = DEFAULT_RETENTION_POLICY
        assert policy.raw_media_retention_seconds == 0
        assert policy.allow_raw_media_storage is False
        assert policy.semantic_event_retention_days == 30
        assert policy.audit_retention_days == 365

    def test_valid_custom_policy_without_raw_media(self) -> None:
        policy = RetentionPolicy(
            semantic_event_retention_days=7,
            audit_retention_days=90,
        )
        assert policy.raw_media_retention_seconds == 0

    def test_raw_media_retention_requires_explicit_opt_in(self) -> None:
        with pytest.raises(ValidationError, match="allow_raw_media_storage"):
            RetentionPolicy(
                raw_media_retention_seconds=60,
                semantic_event_retention_days=7,
                audit_retention_days=90,
                allow_raw_media_storage=False,
            )

    def test_raw_media_allowed_when_opted_in(self) -> None:
        policy = RetentionPolicy(
            raw_media_retention_seconds=30,
            semantic_event_retention_days=7,
            audit_retention_days=90,
            allow_raw_media_storage=True,
        )
        assert policy.raw_media_retention_seconds == 30

    def test_retention_days_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            RetentionPolicy(
                semantic_event_retention_days=0,
                audit_retention_days=365,
            )


@pytest.mark.unit
class TestOrchestrationRecommendation:
    def test_valid_low_severity_without_review(self) -> None:
        rec = _recommendation(
            severity=SeverityLevel.LOW,
            requires_human_review=False,
            human_review_status=HumanReviewStatus.NOT_REQUIRED,
        )
        assert rec.requires_human_review is False

    @pytest.mark.parametrize("severity", [SeverityLevel.HIGH, SeverityLevel.CRITICAL])
    def test_high_severity_requires_human_review(self, severity: SeverityLevel) -> None:
        with pytest.raises(ValidationError, match="requires_human_review"):
            _recommendation(
                severity=severity,
                requires_human_review=False,
                human_review_status=HumanReviewStatus.NOT_REQUIRED,
            )

    @pytest.mark.parametrize("severity", [SeverityLevel.HIGH, SeverityLevel.CRITICAL])
    def test_high_severity_cannot_start_approved(self, severity: SeverityLevel) -> None:
        with pytest.raises(ValidationError, match="APPROVED"):
            _recommendation(
                severity=severity,
                requires_human_review=True,
                human_review_status=HumanReviewStatus.APPROVED,
            )

    @pytest.mark.parametrize("severity", [SeverityLevel.HIGH, SeverityLevel.CRITICAL])
    @pytest.mark.parametrize(
        "status",
        [
            HumanReviewStatus.PENDING,
            HumanReviewStatus.REJECTED,
            HumanReviewStatus.ESCALATED,
        ],
    )
    def test_high_severity_valid_initial_statuses(
        self,
        severity: SeverityLevel,
        status: HumanReviewStatus,
    ) -> None:
        rec = _recommendation(
            severity=severity,
            requires_human_review=True,
            human_review_status=status,
        )
        assert rec.severity == severity

    def test_requires_at_least_one_source_event(self) -> None:
        with pytest.raises(ValidationError):
            _recommendation(based_on_events=[])

    def test_high_risk_severities_match_review_policy(self) -> None:
        assert frozenset({"high", "critical"}) == HIGH_RISK_SEVERITIES


@pytest.mark.unit
class TestTemporalGraphModels:
    def test_graph_node_wraps_semantic_event(self) -> None:
        event = _semantic_event()
        node = TemporalGraphNode(node_id=event.event_id, event=event, risk_score=0.4)
        assert node.event.event_id == event.event_id
        assert node.risk_score == 0.4

    def test_graph_edge_fields(self) -> None:
        source_id = uuid4()
        target_id = uuid4()
        edge = TemporalGraphEdge(
            edge_id=uuid4(),
            source_event_id=source_id,
            target_event_id=target_id,
            kind=TemporalEdgeKind.RISK_PROPAGATION,
            weight=0.75,
            created_at=_now(),
        )
        assert edge.kind == TemporalEdgeKind.RISK_PROPAGATION
        assert edge.source_event_id == source_id

    def test_risk_score_bounds(self) -> None:
        event = _semantic_event()
        with pytest.raises(ValidationError):
            TemporalGraphNode(node_id=uuid4(), event=event, risk_score=1.5)


@pytest.mark.unit
class TestPrivacyLevelEnum:
    @pytest.mark.parametrize(
        "level",
        [
            PrivacyLevel.EPHEMERAL,
            PrivacyLevel.SEMANTIC_ONLY,
            PrivacyLevel.AGGREGATED,
            PrivacyLevel.AUDIT_ONLY,
        ],
    )
    def test_all_privacy_levels(self, level: PrivacyLevel) -> None:
        event = _semantic_event(privacy_level=level)
        assert event.privacy_level == level
