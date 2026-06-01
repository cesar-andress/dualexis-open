"""L2 Edge Perception Layer — ephemeral multimodal perception (Framework Layer 2)."""

from dualexis.edge_perception.interfaces import EdgePerceptionService, PerceptionPipeline
from dualexis.edge_perception.models import (
    EDGE_PERCEPTION_LAYER,
    LayerMetadata,
    Modality,
    PerceptionBatch,
    PerceptionFrame,
    PerceptionSignal,
)
from dualexis.edge_perception.service import (
    DefaultEdgePerceptionService,
    PlaceholderEdgePerceptionService,
    create_placeholder_service,
)

__all__ = [
    "EDGE_PERCEPTION_LAYER",
    "DefaultEdgePerceptionService",
    "EdgePerceptionService",
    "LayerMetadata",
    "Modality",
    "PerceptionBatch",
    "PerceptionFrame",
    "PerceptionPipeline",
    "PerceptionSignal",
    "PlaceholderEdgePerceptionService",
    "create_placeholder_service",
]
