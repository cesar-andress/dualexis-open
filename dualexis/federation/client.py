"""Federation client for cross-node event sharing."""

from __future__ import annotations

from dualexis.federation.registry import NodeRegistry
from dualexis.schemas.domain import SafetyEvent


class FederationClient:
    """Placeholder federation client — no real network transport yet."""

    def __init__(self, local_node_id: str, registry: NodeRegistry | None = None) -> None:
        self._local_node_id = local_node_id
        self._registry = registry or NodeRegistry()
        self._shared_events: list[SafetyEvent] = []

    async def share_event(self, event: SafetyEvent, target_node_id: str) -> bool:
        target = self._registry.get(target_node_id)
        if target is None:
            return False
        self._shared_events.append(event)
        return True

    async def receive_events(self) -> list[SafetyEvent]:
        events = list(self._shared_events)
        self._shared_events.clear()
        return events

    @property
    def registry(self) -> NodeRegistry:
        return self._registry
