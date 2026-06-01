"""Unit tests for L1 Privacy Runtime Layer."""

from __future__ import annotations

import pytest

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.privacy_runtime import DefaultPrivacyRuntimeService, TrustBoundary
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal, ZoneDescriptor


@pytest.mark.unit
def test_validate_frame_passes_ephemeral_frame() -> None:
    runtime = DefaultPrivacyRuntimeService()
    frame = PerceptionFrame(modality="video", node_id="edge-001", zone_id="z1")
    assert runtime.validate_frame(frame).value == "passed"


@pytest.mark.unit
def test_validate_signal_rejects_biometric_features() -> None:
    runtime = DefaultPrivacyRuntimeService()
    zone = ZoneDescriptor(zone_id="z1", label="zone-z1", occupancy_estimate=1, activity_level=0.1)
    signal = PerceptionSignal(
        modality=Modality.VIDEO,
        node_id="edge-001",
        zone=zone,
        confidence=0.5,
        features={"face_embedding": 1.0},
    )
    with pytest.raises(PrivacyViolationError):
        runtime.validate_signal(signal)


@pytest.mark.unit
def test_check_egress_blocks_biometric_keys() -> None:
    runtime = DefaultPrivacyRuntimeService()
    with pytest.raises(PrivacyViolationError):
        runtime.check_egress(
            {"student_id": "x"},
            boundary=TrustBoundary.TB5_NETWORK_EGRESS,
        )
