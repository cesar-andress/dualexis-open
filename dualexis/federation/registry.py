"""Registry of federated edge nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class NodeRecord:
    """Metadata for a registered edge node."""

    node_id: str
    endpoint: str
    zone_ids: frozenset[str]
    registered_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    last_seen: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class NodeRegistry:
    """In-memory registry of federated edge nodes."""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeRecord] = {}

    def register(self, node_id: str, endpoint: str, zone_ids: frozenset[str]) -> NodeRecord:
        record = NodeRecord(node_id=node_id, endpoint=endpoint, zone_ids=zone_ids)
        self._nodes[node_id] = record
        return record

    def deregister(self, node_id: str) -> bool:
        return self._nodes.pop(node_id, None) is not None

    def get(self, node_id: str) -> NodeRecord | None:
        return self._nodes.get(node_id)

    def list_nodes(self) -> list[NodeRecord]:
        return list(self._nodes.values())

    def heartbeat(self, node_id: str) -> None:
        record = self._nodes.get(node_id)
        if record is not None:
            updated = NodeRecord(
                node_id=record.node_id,
                endpoint=record.endpoint,
                zone_ids=record.zone_ids,
                registered_at=record.registered_at,
                last_seen=datetime.now(tz=UTC),
            )
            self._nodes[node_id] = updated
