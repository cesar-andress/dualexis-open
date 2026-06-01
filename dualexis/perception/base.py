"""Base perception pipeline with privacy-aware defaults."""

from __future__ import annotations

from abc import abstractmethod
from uuid import uuid4

from dualexis.edge_perception.interfaces import PerceptionPipeline
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal, ZoneDescriptor


class BasePerceptionPipeline(PerceptionPipeline):
    """Shared logic for modality-specific perception pipelines."""

    def __init__(self, node_id: str, modality: Modality) -> None:
        self._node_id = node_id
        self._modality = modality

    @abstractmethod
    async def _extract_signals(self, frame: PerceptionFrame) -> list[PerceptionSignal]:
        """Modality-specific signal extraction — implemented by subclasses."""

    async def process_frame(self, frame: PerceptionFrame) -> list[PerceptionSignal]:
        if frame.modality != self._modality:
            msg = f"Frame modality {frame.modality} does not match pipeline {self._modality}"
            raise ValueError(msg)
        return await self._extract_signals(frame)

    def supported_modalities(self) -> frozenset[str]:
        return frozenset({self._modality.value})

    def _build_zone_descriptor(
        self,
        frame: PerceptionFrame,
        *,
        occupancy: int = 0,
        activity: float = 0.0,
    ) -> ZoneDescriptor:
        return ZoneDescriptor(
            zone_id=frame.zone_id,
            label=f"zone-{frame.zone_id}",
            occupancy_estimate=occupancy,
            activity_level=activity,
        )

    def _make_signal(
        self,
        frame: PerceptionFrame,
        zone: ZoneDescriptor,
        *,
        confidence: float,
        labels: tuple[str, ...],
        features: dict[str, float] | None = None,
    ) -> PerceptionSignal:
        return PerceptionSignal(
            signal_id=str(uuid4()),
            modality=self._modality,
            node_id=self._node_id,
            zone=zone,
            confidence=confidence,
            labels=labels,
            features=features or {},
        )
