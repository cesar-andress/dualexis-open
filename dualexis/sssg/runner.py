"""Build SSSG traces by walking shared world dynamics (aligned with simulation)."""

from __future__ import annotations

import random

from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.event_generator import SyntheticEventGenerator
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.scenario import ScenarioId, get_scenario_definition
from dualexis.simulation.world import build_default_world, initial_world_state
from dualexis.simulation.world_dynamics import advance_world_state
from dualexis.sssg.metrics import StateGraphMetrics, compute_state_graph_metrics
from dualexis.sssg.models import StateTransitionTrace
from dualexis.sssg.service import SemanticSafetyStateGraphService


def build_sssg_trace_from_scenario(
    scenario: str,
    *,
    seed: int = 1,
    location_id: str = "sssg-site",
) -> StateTransitionTrace:
    """Walk world dynamics + events and record safety-state transitions."""
    scenario_id = ScenarioId(scenario)
    definition = get_scenario_definition(scenario_id)
    rng = random.Random(seed)
    graph = build_default_world(location_id=location_id)
    state = initial_world_state(graph)
    event_gen = SyntheticEventGenerator()
    sssg = SemanticSafetyStateGraphService(scenario_id=scenario, seed=seed)
    zone_ids = tuple(state.zone_density)

    for _step in range(definition.duration_steps):
        state = advance_world_state(state, graph, definition, scenario_id, rng)
        for zone_id in zone_ids:
            sssg.ingest_world_evidence(
                state,
                zone_id=zone_id,
                timestamp=event_gen.timestamp_for_tick(state.tick, tick_seconds=definition.tick_seconds),
                peer_zones=zone_ids,
            )
        tick_events = event_gen.generate_events(
            state,
            scenario_id=scenario_id,
            tick_seconds=definition.tick_seconds,
        )
        for event in tick_events:
            event = event.model_copy(
                update={"metadata": {**event.metadata, "tick": str(state.tick)}}
            )
            sssg.ingest_semantic_event(event, peer_zones=zone_ids)

    return sssg.graph.to_trace()


def evaluate_sssg_trace(
    scenario: str,
    *,
    seed: int = 1,
) -> tuple[StateTransitionTrace, StateGraphMetrics]:
    trace = build_sssg_trace_from_scenario(scenario, seed=seed)
    gt = load_scenario_ground_truth(ScenarioId(scenario))
    metrics = compute_state_graph_metrics(trace, gt)
    return trace, metrics


__all__ = [
    "build_sssg_trace_from_scenario",
    "evaluate_sssg_trace",
]
