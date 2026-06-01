"""Tests for multimodal fusion engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from dualexis.fusion.engine import DefaultFusionEngine
from dualexis.schemas.fusion import FusionInput, ModalityWeight
from dualexis.schemas.perception import Modality, PerceptionSignal, ZoneDescriptor


def _make_signal(
    modality: Modality, labels: tuple[str, ...], confidence: float
) -> PerceptionSignal:
    zone = ZoneDescriptor(
        zone_id="hallway-a",
        label="Hallway A",
        occupancy_estimate=10,
        activity_level=0.5,
    )
    return PerceptionSignal(
        modality=modality,
        node_id="edge-001",
        zone=zone,
        confidence=confidence,
        labels=labels,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fusion_combines_multimodal_signals() -> None:
    engine = DefaultFusionEngine()
    now = datetime.now(tz=UTC)
    fusion_input = FusionInput(
        node_id="edge-001",
        zone_id="hallway-a",
        window_start=now - timedelta(seconds=5),
        window_end=now,
        signals=(
            _make_signal(Modality.VIDEO, ("movement_detected",), 0.8),
            _make_signal(Modality.AUDIO, ("elevated_noise_level",), 0.7),
        ),
        weights=(ModalityWeight(modality="video", weight=0.6),),
    )
    result = await engine.fuse(fusion_input)
    assert result.fused_confidence > 0.0
    assert len(result.fused_labels) >= 1
    assert len(result.signal_ids) == 2
