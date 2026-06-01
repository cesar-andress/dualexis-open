"""Simulation layer — reproducible confined-space benchmark environment."""

from dualexis.simulation.interfaces import SimulationService
from dualexis.simulation.models import (
    SIMULATION_LAYER,
    LayerMetadata,
    SimulationScenario,
    SyntheticFrameBatch,
)
from dualexis.simulation.runner import SimulationResult, SimulationRunner, run_scenario
from dualexis.simulation.scenario import ScenarioId, UnknownScenarioError, get_scenario_definition
from dualexis.simulation.service import (
    DefaultSimulationService,
    PlaceholderSimulationService,
)

__all__ = [
    "SIMULATION_LAYER",
    "DefaultSimulationService",
    "LayerMetadata",
    "PlaceholderSimulationService",
    "ScenarioDefinition",
    "ScenarioId",
    "SimulationResult",
    "SimulationRunner",
    "SimulationScenario",
    "SimulationService",
    "SyntheticFrameBatch",
    "UnknownScenarioError",
    "get_scenario_definition",
    "run_scenario",
]
