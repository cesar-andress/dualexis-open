"""Simulation layer — default synthetic batch and scenario runner."""

from __future__ import annotations

from dualexis.simulation.interfaces import SimulationService
from dualexis.simulation.models import (
    SimulationScenario,
    SyntheticFrameBatch,
    build_synthetic_batch,
)
from dualexis.simulation.runner import SimulationResult, SimulationRunner, run_scenario
from dualexis.simulation.scenario import ScenarioId


class DefaultSimulationService(SimulationService):
    """Produces deterministic synthetic inputs and reproducible scenario runs."""

    def generate_batch(
        self,
        scenario: SimulationScenario,
        *,
        node_id: str,
        zone_id: str,
    ) -> SyntheticFrameBatch:
        return build_synthetic_batch(scenario, node_id=node_id, zone_id=zone_id)

    def run_reproducible(
        self,
        scenario_id: ScenarioId,
        *,
        seed: int = 42,
        node_id: str = "sim-edge-001",
        location_id: str = "sim-school-north",
    ) -> SimulationResult:
        """Run a confined-space scenario with deterministic seed."""
        return SimulationRunner(
            scenario_id=scenario_id,
            seed=seed,
            node_id=node_id,
            location_id=location_id,
        ).run()


PlaceholderSimulationService = DefaultSimulationService

__all__ = ["DefaultSimulationService", "PlaceholderSimulationService", "run_scenario"]
