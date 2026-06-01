"""L6 Human-in-the-Loop Orchestration Layer — service interfaces.

Maps to DUALEXIS Framework Layer 6 (Human-in-the-Loop Orchestration Layer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dualexis.schemas.domain import SafetyEvent
from dualexis.schemas.perception import PerceptionFrame


class OrchestrationService(ABC):
    """End-to-end safety orchestration with human-in-the-loop semantics."""

    @abstractmethod
    async def process_frames(
        self,
        frames: list[PerceptionFrame],
        *,
        zone_id: str,
    ) -> SafetyEvent:
        """Run the full L2-L6 pipeline for a batch of ephemeral frames."""
