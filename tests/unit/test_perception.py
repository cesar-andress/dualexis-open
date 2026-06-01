"""Tests for perception schemas and pipelines."""

from __future__ import annotations

import pytest

from dualexis.perception.audio.pipeline import AudioPerceptionPipeline
from dualexis.perception.video.pipeline import VideoPerceptionPipeline
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal, ZoneDescriptor


@pytest.mark.unit
def test_zone_descriptor_rejects_biometric_metadata() -> None:
    with pytest.raises(ValueError, match="Biometric"):
        ZoneDescriptor(
            zone_id="hallway-a",
            label="Hallway A",
            occupancy_estimate=5,
            activity_level=0.3,
            metadata={"face_id": "123"},
        )


@pytest.mark.unit
def test_perception_signal_rejects_identity_labels() -> None:
    zone = ZoneDescriptor(
        zone_id="hallway-a",
        label="Hallway A",
        occupancy_estimate=5,
        activity_level=0.3,
    )
    with pytest.raises(ValueError, match="forbidden"):
        PerceptionSignal(
            modality=Modality.VIDEO,
            node_id="edge-001",
            zone=zone,
            confidence=0.8,
            labels=("student_identified",),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_video_pipeline_produces_zone_level_signals() -> None:
    pipeline = VideoPerceptionPipeline("edge-001")
    frame = PerceptionFrame(modality=Modality.VIDEO, node_id="edge-001", zone_id="hallway-a")
    signals = await pipeline.process_frame(frame)
    assert len(signals) == 1
    assert signals[0].modality == Modality.VIDEO
    assert "face" not in " ".join(signals[0].labels).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audio_pipeline_no_speaker_id() -> None:
    pipeline = AudioPerceptionPipeline("edge-001")
    frame = PerceptionFrame(modality=Modality.AUDIO, node_id="edge-001", zone_id="cafeteria")
    signals = await pipeline.process_frame(frame)
    assert all("speaker" not in label for label in signals[0].labels)
