"""L2 Edge Perception Layer — data models.

Maps to DUALEXIS Framework Layer 2 (Edge Perception Layer).
Transforms ephemeral multimodal frames into zone-level perception signals.
"""

from __future__ import annotations

from dataclasses import dataclass

from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal, ZoneDescriptor


@dataclass(frozen=True)
class LayerMetadata:
    """Static descriptor for the edge perception framework layer."""

    layer_id: str = "L2"
    name: str = "edge_perception"
    processes_events_only: bool = True


@dataclass(frozen=True)
class PerceptionBatch:
    """Ephemeral batch of zone-level signals extracted at the edge."""

    node_id: str
    zone_id: str
    signals: tuple[PerceptionSignal, ...]


EDGE_PERCEPTION_LAYER = LayerMetadata()

__all__ = [
    "EDGE_PERCEPTION_LAYER",
    "LayerMetadata",
    "Modality",
    "PerceptionBatch",
    "PerceptionFrame",
    "PerceptionSignal",
    "ZoneDescriptor",
]
