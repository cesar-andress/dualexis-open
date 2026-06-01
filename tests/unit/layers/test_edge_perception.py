"""Unit tests for L2 Edge Perception Layer."""

from __future__ import annotations

import pytest

from dualexis.edge_perception import DefaultEdgePerceptionService
from dualexis.perception.video.pipeline import VideoPerceptionPipeline
from dualexis.schemas.perception import Modality, PerceptionFrame


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_frames_returns_signals() -> None:
    node_id = "edge-001"
    service = DefaultEdgePerceptionService(
        {Modality.VIDEO.value: VideoPerceptionPipeline(node_id)},
    )
    frames = [PerceptionFrame(modality=Modality.VIDEO, node_id=node_id, zone_id="z1")]
    signals = await service.process_frames(frames)
    assert len(signals) == 1
    assert signals[0].zone.zone_id == "z1"
