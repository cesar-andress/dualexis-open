"""L3 Semantic Event Layer — service interfaces.

Maps to DUALEXIS Framework Layer 3 (Semantic Event Layer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dualexis.schemas.domain import FusionResult, SafetyEvent
from dualexis.schemas.fusion import FusionInput


class SemanticEventService(ABC):
    """Fuses perception signals and materializes explainable safety events."""

    @abstractmethod
    async def fuse_signals(self, fusion_input: FusionInput) -> FusionResult:
        """Combine multimodal signals into a fusion result."""

    @abstractmethod
    def build_safety_event(
        self,
        fusion_result: FusionResult,
        *,
        node_id: str,
        zone_id: str,
    ) -> SafetyEvent:
        """Materialize a canonical SafetyEvent from fusion output."""
