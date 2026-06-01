"""Basic event flow example — run with: uv run python examples/basic_event_flow/run.py"""

from __future__ import annotations

import asyncio
import logging

from apps.edge_node.main import build_orchestrator
from dualexis.schemas.perception import Modality, PerceptionFrame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    node_id = "example-edge-001"
    zone_id = "library-west"
    orchestrator = build_orchestrator(node_id)

    frames = [
        PerceptionFrame(modality=Modality.VIDEO, node_id=node_id, zone_id=zone_id),
        PerceptionFrame(modality=Modality.AUDIO, node_id=node_id, zone_id=zone_id),
        PerceptionFrame(modality=Modality.SENSOR, node_id=node_id, zone_id=zone_id),
    ]

    event = await orchestrator.process_frames(frames, zone_id=zone_id)
    logger.info("Event ID: %s", event.event_id)
    logger.info("Severity: %s", event.severity.value)
    logger.info("Status: %s", event.status.value)
    logger.info("Descriptors: %s", [d.description for d in event.descriptors])
    logger.info("Requires human review: %s", event.requires_human_review)


if __name__ == "__main__":
    asyncio.run(main())
