"""Privacy fuzz tests for forbidden fields and raw-media leakage (validation package)."""

from __future__ import annotations

import pytest

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.pipeline import run_pipeline
from dualexis.privacy_runtime import (
    DEFAULT_PRIVACY_POLICY,
    DefaultPrivacyRuntimeService,
    strip_raw_media,
    validate_payload_privacy,
)
from dualexis.privacy_runtime.models import FORBIDDEN_FIELDS
from dualexis.schemas.perception import Modality, PerceptionFrame


@pytest.mark.unit
@pytest.mark.parametrize("field_name", sorted(FORBIDDEN_FIELDS))
def test_forbidden_field_fuzz_rejected(field_name: str) -> None:
    with pytest.raises(PrivacyViolationError):
        validate_payload_privacy({field_name: "injected"}, DEFAULT_PRIVACY_POLICY)


@pytest.mark.unit
def test_raw_media_paths_stripped_and_not_retained() -> None:
    payload = {
        "zone_id": "hall-a",
        "raw_video_path": "/tmp/clip.mp4",
        "raw_audio_path": "/tmp/clip.wav",
        "frame_data": "ephemeral-bytes-not-stored",
    }
    sanitized = strip_raw_media(payload)
    for key in ("raw_video_path", "raw_audio_path", "frame_data"):
        assert key not in sanitized


@pytest.mark.unit
def test_pipeline_output_events_have_no_raw_media_flag() -> None:
    output = run_pipeline("normal_flow", seed=7)
    for event in output.normalized_events:
        assert event.raw_media_persisted is False
    assert output.privacy_report.raw_media_bytes_persisted == 0


@pytest.mark.unit
def test_persistent_media_frame_rejected_by_runtime() -> None:
    runtime = DefaultPrivacyRuntimeService()
    frame = PerceptionFrame(
        modality=Modality.VIDEO,
        node_id="fuzz-node",
        zone_id="cafeteria",
        payload_ref="/var/dualexis/forbidden_clip.mp4",
    )
    with pytest.raises(PrivacyViolationError):
        runtime.validate_frame(frame)
