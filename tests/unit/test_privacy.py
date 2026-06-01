"""Tests for privacy guard and policies."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.privacy.guard import DefaultPrivacyGuard
from dualexis.schemas.events import EventSeverity, SafetyEvent, SemanticDescriptor
from dualexis.schemas.perception import Modality, PerceptionSignal, ZoneDescriptor
from dualexis.schemas.privacy import PrivacyPolicy


@pytest.mark.unit
def test_strict_policy_rejects_biometrics() -> None:
    with pytest.raises(ValueError, match="Biometric"):
        PrivacyPolicy(
            policy_id="bad",
            name="Bad Policy",
            allow_biometric_features=True,
        )


@pytest.mark.unit
def test_privacy_guard_rejects_biometric_features() -> None:
    guard = DefaultPrivacyGuard()
    zone = ZoneDescriptor(
        zone_id="hallway-a",
        label="Hallway A",
        occupancy_estimate=3,
        activity_level=0.2,
    )
    signal = PerceptionSignal(
        modality=Modality.VIDEO,
        node_id="edge-001",
        zone=zone,
        confidence=0.7,
        features={"face_embedding": 0.99},
    )
    with pytest.raises(PrivacyViolationError):
        guard.validate_signal(signal)


@pytest.mark.unit
def test_semantic_descriptor_rejects_raw_media_in_evidence() -> None:
    with pytest.raises(ValueError, match="raw_video"):
        SemanticDescriptor(
            category="test",
            description="Test event",
            confidence=0.5,
            evidence={"raw_video": "ephemeral-buffer-ref"},
        )


@pytest.mark.unit
def test_privacy_guard_rejects_raw_media_in_events() -> None:
    guard = DefaultPrivacyGuard()
    event = SafetyEvent.model_construct(
        event_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        node_id="edge-001",
        zone_id="hallway-a",
        severity=EventSeverity.LOW,
        descriptors=(
            SemanticDescriptor.model_construct(
                category="test",
                description="Test event",
                confidence=0.5,
                evidence={"raw_audio": "buffer-ref"},
            ),
        ),
    )
    with pytest.raises(PrivacyViolationError):
        guard.validate_event(event)


@pytest.mark.unit
def test_default_policy_is_strict() -> None:
    guard = DefaultPrivacyGuard()
    policy = guard.active_policy()
    assert policy.allow_biometric_features is False
    assert policy.allow_persistent_media is False
    assert policy.max_buffer_ttl <= timedelta(minutes=1)
