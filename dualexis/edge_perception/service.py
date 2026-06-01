"""L2 Edge Perception Layer — default service implementation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from dualexis.edge_perception.interfaces import EdgePerceptionService, PerceptionPipeline
from dualexis.edge_perception.models import PerceptionFrame, PerceptionSignal


class DefaultEdgePerceptionService(EdgePerceptionService):
    """Runs modality pipelines on ephemeral frames at the edge."""

    def __init__(self, pipelines: Mapping[str, PerceptionPipeline] | None = None) -> None:
        self._pipelines = dict(pipelines or {})

    async def process_frames(
        self,
        frames: Sequence[PerceptionFrame],
    ) -> tuple[PerceptionSignal, ...]:
        signals: list[PerceptionSignal] = []
        for frame in frames:
            pipeline = self._pipelines.get(frame.modality.value)
            if pipeline is None:
                continue
            extracted = await pipeline.process_frame(frame)
            signals.extend(extracted)
        return tuple(signals)

    def pipelines(self) -> Mapping[str, PerceptionPipeline]:
        return self._pipelines


PlaceholderEdgePerceptionService = DefaultEdgePerceptionService


def create_placeholder_service(
    pipelines: Mapping[str, PerceptionPipeline] | None = None,
) -> DefaultEdgePerceptionService:
    """Build an edge perception service with optional modality pipelines."""
    return DefaultEdgePerceptionService(pipelines)
