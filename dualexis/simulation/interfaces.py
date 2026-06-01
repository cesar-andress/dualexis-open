"""Simulation layer — service interfaces.

Maps to synthetic scenario generation for reproducible pipeline testing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dualexis.simulation.models import SimulationScenario, SyntheticFrameBatch


class SimulationService(ABC):
    """Generates synthetic ephemeral inputs for orchestration testing."""

    @abstractmethod
    def generate_batch(
        self,
        scenario: SimulationScenario,
        *,
        node_id: str,
        zone_id: str,
    ) -> SyntheticFrameBatch:
        """Return a synthetic frame batch without persistent media."""
