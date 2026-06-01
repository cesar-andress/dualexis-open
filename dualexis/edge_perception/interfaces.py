"""L2 Edge Perception Layer — service interfaces.

Maps to DUALEXIS Framework Layer 2 (Edge Perception Layer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence

from dualexis.edge_perception.models import PerceptionFrame, PerceptionSignal


class PerceptionPipeline(ABC):
    """Modality-specific edge perception pipeline (no biometrics)."""

    @abstractmethod
    async def process_frame(self, frame: PerceptionFrame) -> list[PerceptionSignal]:
        """Extract zone-level signals from an ephemeral frame."""

    @abstractmethod
    def supported_modalities(self) -> frozenset[str]:
        """Return supported modality identifiers."""


class EdgePerceptionService(ABC):
    """Coordinates edge perception pipelines for multimodal input."""

    @abstractmethod
    async def process_frames(
        self,
        frames: Sequence[PerceptionFrame],
    ) -> tuple[PerceptionSignal, ...]:
        """Process frames through registered pipelines and return all signals."""

    @abstractmethod
    def pipelines(self) -> Mapping[str, PerceptionPipeline]:
        """Return registered modality pipelines."""
