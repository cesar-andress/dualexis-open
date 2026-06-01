"""Tests for the placeholder fusion engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from dualexis.fusion.engine import DefaultFusionEngine
from dualexis.schemas.fusion import FusionInput
from dualexis.schemas.perception import Modality, PerceptionSignal, ZoneDescriptor


def _normalized_signal(
    *,
    modality: Modality,
    labels: tuple[str, ...],
    confidence: float,
    signal_id: str,
) -> PerceptionSignal:
    """Build a privacy-normalized perception signal for fusion input."""
    zone = ZoneDescriptor(
        zone_id="hallway-a",
        label="Hallway A",
        occupancy_estimate=8,
        activity_level=0.4,
    )
    return PerceptionSignal(
        signal_id=signal_id,
        modality=modality,
        node_id="edge-001",
        zone=zone,
        confidence=confidence,
        labels=labels,
        features={"activity_score": confidence},
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fusion_engine_accepts_normalized_signals() -> None:
    engine = DefaultFusionEngine()
    now = datetime.now(tz=UTC)
    fusion_input = FusionInput(
        node_id="edge-001",
        zone_id="hallway-a",
        window_start=now - timedelta(seconds=5),
        window_end=now,
        signals=(
            _normalized_signal(
                modality=Modality.VIDEO,
                labels=("movement_detected",),
                confidence=0.75,
                signal_id="sig-video-1",
            ),
            _normalized_signal(
                modality=Modality.AUDIO,
                labels=("elevated_noise_level",),
                confidence=0.65,
                signal_id="sig-audio-1",
            ),
        ),
    )
    result = await engine.fuse(fusion_input)
    assert 0.0 < result.fused_confidence <= 1.0
    assert result.explanation
    assert result.confidence.rationale
    assert result.fused_labels
    assert set(result.signal_ids) == {"sig-video-1", "sig-audio-1"}
    assert "video" in result.modality_contributions
    assert "audio" in result.modality_contributions
