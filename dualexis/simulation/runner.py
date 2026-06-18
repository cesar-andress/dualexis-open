"""Reproducible simulation runner for DUALEXIS benchmarks."""

from __future__ import annotations

import random
from dataclasses import dataclass

from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.emission_mode import EmissionMode
from dualexis.simulation.event_generator import SyntheticEventGenerator
from dualexis.simulation.ground_truth import ScenarioGroundTruth
from dualexis.simulation.independent_labeler import build_independent_ground_truth
from dualexis.simulation.scenario import ScenarioId, get_scenario_definition, resolve_scenario
from dualexis.simulation.world import ConfinedSpaceGraph, WorldState, build_default_world, initial_world_state
from dualexis.simulation.world_dynamics import advance_world_state


@dataclass(frozen=True)
class SimulationResult:
    """Output of a reproducible simulation run."""

    scenario_id: ScenarioId
    seed: int
    graph: ConfinedSpaceGraph
    events: tuple[SemanticEvent, ...]
    ground_truth: ScenarioGroundTruth
    final_state: WorldState | None = None
    emission_mode: EmissionMode = EmissionMode.DECOUPLED


@dataclass
class SimulationRunner:
    """Deterministic confined-space simulator producing semantic events only."""

    scenario_id: ScenarioId
    seed: int = 42
    node_id: str = "sim-edge-001"
    location_id: str = "sim-school-north"
    emission_mode: EmissionMode = EmissionMode.DECOUPLED

    def run(self) -> SimulationResult:
        """Execute the simulation and return synthetic events plus ground truth."""
        definition = get_scenario_definition(self.scenario_id)
        rng = random.Random(self.seed)
        graph = build_default_world(location_id=self.location_id)
        state = initial_world_state(graph)
        generator = SyntheticEventGenerator(
            node_id=self.node_id,
            emission_mode=self.emission_mode,
            seed=self.seed,
        )

        all_events: list[SemanticEvent] = []

        for _step in range(definition.duration_steps):
            state = advance_world_state(state, graph, definition, self.scenario_id, rng)
            tick_events = generator.generate_events(
                state,
                scenario_id=self.scenario_id,
                tick_seconds=definition.tick_seconds,
            )
            all_events.extend(tick_events)

        ground_truth = build_independent_ground_truth(self.scenario_id, seed=self.seed)

        return SimulationResult(
            scenario_id=self.scenario_id,
            seed=self.seed,
            graph=graph,
            events=tuple(all_events),
            ground_truth=ground_truth,
            final_state=state,
            emission_mode=self.emission_mode,
        )


def run_scenario(
    name: str,
    *,
    seed: int = 42,
    emission_mode: EmissionMode = EmissionMode.DECOUPLED,
) -> SimulationResult:
    """Run a reproducible confined-space scenario by name with a deterministic seed."""
    scenario_id = resolve_scenario(name)
    return SimulationRunner(scenario_id=scenario_id, seed=seed, emission_mode=emission_mode).run()


__all__ = ["SimulationResult", "SimulationRunner", "run_scenario"]
