"""Simulator application — generates synthetic perception frames for testing."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from apps.edge_node.main import build_orchestrator
from dualexis.schemas.perception import Modality, PerceptionFrame

logger = logging.getLogger(__name__)


async def run_simulation(
    *,
    node_id: str = "sim-edge-001",
    zone_id: str = "playground-north",
    num_cycles: int = 3,
) -> None:
    orchestrator = build_orchestrator(node_id)
    logger.info("Running simulation: %d cycles in zone '%s'", num_cycles, zone_id)

    for cycle in range(num_cycles):
        frames = [
            PerceptionFrame(
                frame_id=str(uuid4()),
                modality=Modality.VIDEO,
                node_id=node_id,
                zone_id=zone_id,
            ),
            PerceptionFrame(
                frame_id=str(uuid4()),
                modality=Modality.AUDIO,
                node_id=node_id,
                zone_id=zone_id,
            ),
            PerceptionFrame(
                frame_id=str(uuid4()),
                modality=Modality.SENSOR,
                node_id=node_id,
                zone_id=zone_id,
            ),
        ]
        event = await orchestrator.process_frames(frames, zone_id=zone_id)
        logger.info(
            "Cycle %d: event=%s severity=%s labels=%s",
            cycle + 1,
            event.event_id,
            event.severity.value,
            [d.category for d in event.descriptors],
        )


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_simulation())


if __name__ == "__main__":
    run()
