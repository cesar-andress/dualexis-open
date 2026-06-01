"""Unit tests for DUALEXIS privacy runtime enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.orchestration.models import SeverityLevel
from dualexis.pipeline import run_pipeline
from dualexis.privacy_runtime import (
    DEFAULT_PRIVACY_POLICY,
    DefaultPrivacyRuntimeService,
    PrivacyReport,
    PrivacyViolationType,
    enforce_retention_policy,
    strip_raw_media,
    validate_payload_privacy,
)
from dualexis.privacy_runtime.models import FORBIDDEN_FIELDS, PrivacyLevel
from dualexis.schemas.audit import AuditAction, AuditEntry
from dualexis.schemas.domain import SafetyEvent
from dualexis.schemas.events import EventSeverity, SemanticDescriptor
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal, ZoneDescriptor
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent


def _zone() -> ZoneDescriptor:
    return ZoneDescriptor(
        zone_id="hall-a",
        label="zone-hall-a",
        occupancy_estimate=5,
        activity_level=0.2,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    sorted(FORBIDDEN_FIELDS),
)
def test_forbidden_fields_are_rejected(field_name: str) -> None:
    with pytest.raises(PrivacyViolationError):
        validate_payload_privacy({field_name: "blocked"}, DEFAULT_PRIVACY_POLICY)


@pytest.mark.unit
def test_raw_media_is_stripped() -> None:
    payload = {
        "zone_id": "hall-a",
        "raw_video_path": "/tmp/video.mp4",
        "raw_audio_path": "/tmp/audio.wav",
        "density": "0.42",
    }
    sanitized = strip_raw_media(payload)
    assert "raw_video_path" not in sanitized
    assert "raw_audio_path" not in sanitized
    assert sanitized["density"] == "0.42"


@pytest.mark.unit
def test_zero_retention_policy_is_default() -> None:
    policy = DEFAULT_PRIVACY_POLICY
    assert policy.raw_video_retention_seconds == 0
    assert policy.raw_audio_retention_seconds == 0
    assert policy.allow_persistent_media is False

    video_decision = enforce_retention_policy(policy, artifact_kind="raw_video")
    audio_decision = enforce_retention_policy(policy, artifact_kind="raw_audio")
    event_decision = enforce_retention_policy(policy, artifact_kind="semantic_event")

    assert video_decision.may_retain is False
    assert audio_decision.may_retain is False
    assert event_decision.may_retain is True
    assert event_decision.retention_seconds == policy.semantic_event_retention_days * 86_400


@pytest.mark.unit
def test_semantic_events_pass_validation() -> None:
    runtime = DefaultPrivacyRuntimeService()
    event = SemanticEvent(
        event_id=uuid4(),
        event_type=EventType.CROWD_ACCELERATION,
        source=EventSource.SIMULATOR,
        zone_id="cafeteria",
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        confidence=0.72,
        severity=SeverityLevel.MEDIUM,
        explanation="Zone-level crowd acceleration based on aggregate motion descriptors.",
        privacy_level=PrivacyLevel.SEMANTIC_ONLY,
        metadata={"category": "density_elevated"},
    )
    validated = runtime.validate_semantic_event(event)
    assert isinstance(validated, SemanticEvent)
    assert validated.event_type == EventType.CROWD_ACCELERATION


@pytest.mark.unit
def test_privacy_report_is_generated() -> None:
    runtime = DefaultPrivacyRuntimeService()
    runtime.validate_frame(PerceptionFrame(modality="video", node_id="edge-001", zone_id="hall-a"))
    report = runtime.build_report()
    assert isinstance(report, PrivacyReport)
    assert report.policy_id == DEFAULT_PRIVACY_POLICY.policy_id
    assert report.policy_compliant is True
    assert report.raw_video_retention_seconds == 0
    assert report.raw_audio_retention_seconds == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_fails_closed_on_privacy_violations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dualexis.pipeline.service import (
        create_default_pipeline_service,
        pipeline_inputs_from_scenario,
    )

    service = create_default_pipeline_service()
    inputs = pipeline_inputs_from_scenario("exit_blockage", seed=42)

    async def _emit_forbidden_signal(_frames: object) -> list[PerceptionSignal]:
        return [
            PerceptionSignal(
                modality=Modality.VIDEO,
                node_id="pipeline-edge-001",
                zone=_zone(),
                confidence=0.5,
                features={"person_id": 1.0},
            )
        ]

    monkeypatch.setattr(service._perception, "process_frames", _emit_forbidden_signal)

    with pytest.raises(PrivacyViolationError):
        await service.run(inputs, scenario_name="exit_blockage", seed=42)


@pytest.mark.unit
def test_high_risk_events_require_audit_records() -> None:
    runtime = DefaultPrivacyRuntimeService()
    event = SafetyEvent.model_construct(
        event_id=uuid4(),
        node_id="edge-001",
        zone_id="exit-c",
        severity=EventSeverity.HIGH,
        descriptors=(
            SemanticDescriptor.model_construct(
                category="exit_blockage",
                description="Exit obstructed",
                confidence=0.9,
            ),
        ),
    )
    with pytest.raises(PrivacyViolationError, match="audit"):
        runtime.ensure_high_risk_audit([event], [])


@pytest.mark.unit
def test_high_risk_events_pass_with_audit_records() -> None:
    runtime = DefaultPrivacyRuntimeService()
    event = SafetyEvent.model_construct(
        event_id=uuid4(),
        node_id="edge-001",
        zone_id="exit-c",
        severity=EventSeverity.HIGH,
        descriptors=(
            SemanticDescriptor.model_construct(
                category="exit_blockage",
                description="Exit obstructed",
                confidence=0.9,
            ),
        ),
    )
    audit = (
        AuditEntry(
            entry_id="audit-1",
            action=AuditAction.FUSION_COMPLETED,
            node_id="edge-001",
        ),
    )
    runtime.ensure_high_risk_audit([event], audit)


@pytest.mark.unit
def test_pipeline_output_includes_privacy_report() -> None:
    output = run_pipeline("exit_blockage", seed=42)
    assert isinstance(output.privacy_report, PrivacyReport)
    assert output.privacy_report.policy_compliant is True
    assert output.privacy_report.policy_id == DEFAULT_PRIVACY_POLICY.policy_id


@pytest.mark.unit
def test_sanitize_frame_strips_payload_ref() -> None:
    runtime = DefaultPrivacyRuntimeService()
    frame = PerceptionFrame(
        modality=Modality.VIDEO,
        node_id="edge-001",
        zone_id="hall-a",
        payload_ref="/data/ephemeral/frame.bin",
    )
    with pytest.raises(PrivacyViolationError):
        runtime.validate_frame(frame)

    ephemeral = PerceptionFrame(
        modality=Modality.VIDEO,
        node_id="edge-001",
        zone_id="hall-a",
        payload_ref="memory-buffer-001",
    )
    runtime.validate_frame(ephemeral)
    stripped = runtime.sanitize_frame(ephemeral)
    assert stripped.payload_ref is None


@pytest.mark.unit
def test_violation_type_classification() -> None:
    runtime = DefaultPrivacyRuntimeService()
    with pytest.raises(PrivacyViolationError):
        try:
            runtime.validate_signal(
                PerceptionSignal(
                    modality=Modality.AUDIO,
                    node_id="edge-001",
                    zone=_zone(),
                    confidence=0.5,
                    features={"voiceprint": 0.9},
                )
            )
        except PrivacyViolationError:
            report = runtime.build_report(high_risk_audit_satisfied=True)
            assert report.personal_data_violations >= 1
            assert report.violations[0].violation_type == PrivacyViolationType.BIOMETRIC
            raise
