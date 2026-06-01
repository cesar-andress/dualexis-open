"""Edge node application — ephemeral perception at the boundary."""

from __future__ import annotations

import asyncio
import logging

from apps.services import build_safety_orchestrator
from dualexis.core.config import Settings
from dualexis.orchestration.service import SafetyOrchestrator
from dualexis.perception.audio.pipeline import AudioPerceptionPipeline
from dualexis.perception.sensors.pipeline import SensorPerceptionPipeline
from dualexis.perception.video.pipeline import VideoPerceptionPipeline
from dualexis.schemas.perception import Modality, PerceptionFrame

logger = logging.getLogger(__name__)


def build_orchestrator(node_id: str) -> SafetyOrchestrator:
    pipelines = {
        Modality.VIDEO.value: VideoPerceptionPipeline(node_id),
        Modality.AUDIO.value: AudioPerceptionPipeline(node_id),
        Modality.SENSOR.value: SensorPerceptionPipeline(node_id),
    }
    return build_safety_orchestrator(node_id, pipelines)


async def run_edge_node(node_id: str = "edge-001", zone_id: str = "hallway-a") -> None:
    settings = Settings()
    logger.info(
        "Starting edge node %s (buffer TTL: %ss)", node_id, settings.edge_buffer_ttl_seconds
    )

    orchestrator = build_orchestrator(node_id)
    frames = [
        PerceptionFrame(modality=Modality.VIDEO, node_id=node_id, zone_id=zone_id),
        PerceptionFrame(modality=Modality.AUDIO, node_id=node_id, zone_id=zone_id),
    ]
    event = await orchestrator.process_frames(frames, zone_id=zone_id)
    logger.info("Processed event %s with severity %s", event.event_id, event.severity.value)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_edge_node())


if __name__ == "__main__":
    run()
