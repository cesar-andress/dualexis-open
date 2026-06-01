"""Orchestrator application — coordinates multiple edge nodes."""

from __future__ import annotations

import asyncio
import logging

from dualexis.federation.client import FederationClient
from dualexis.federation.registry import NodeRegistry

logger = logging.getLogger(__name__)


async def run_orchestrator() -> None:
    registry = NodeRegistry()
    registry.register("edge-001", "http://localhost:8001", frozenset({"hallway-a", "hallway-b"}))
    registry.register("edge-002", "http://localhost:8002", frozenset({"cafeteria"}))

    client = FederationClient(local_node_id="orchestrator-001", registry=registry)
    nodes = client.registry.list_nodes()
    logger.info("Orchestrator managing %d edge nodes", len(nodes))
    for node in nodes:
        logger.info("  - %s @ %s (zones: %s)", node.node_id, node.endpoint, sorted(node.zone_ids))


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_orchestrator())


if __name__ == "__main__":
    run()
