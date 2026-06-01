"""Anonymous world-state dynamics shared by simulation and independent GT authoring.

This module intentionally excludes ``SyntheticEventGenerator`` and semantic-event
emission so ground-truth labelers can advance the world without event-generation logic.
"""

from __future__ import annotations

import random

from dualexis.simulation.scenario import ScenarioDefinition, ScenarioId
from dualexis.simulation.world import ConfinedSpaceGraph, FlowEntity, WorldState


def advance_world_state(
    state: WorldState,
    graph: ConfinedSpaceGraph,
    definition: ScenarioDefinition,
    scenario_id: ScenarioId,
    rng: random.Random,
) -> WorldState:
    """Advance one tick of zone metrics for *scenario_id* (no event emission)."""
    _ = graph
    tick = state.tick + 1
    elapsed = tick * definition.tick_seconds
    density = dict(state.zone_density)
    activity = dict(state.zone_activity)
    audio = dict(state.zone_audio_stress)
    exit_tp = dict(state.exit_throughput)

    def noise(base: float) -> float:
        return max(0.0, min(1.0, base + rng.uniform(-0.02, 0.02)))

    if scenario_id == ScenarioId.NORMAL_FLOW:
        for zone_id in density:
            density[zone_id] = noise(0.25)
            activity[zone_id] = noise(0.2)
            audio[zone_id] = noise(0.1)

    elif scenario_id == ScenarioId.CROWD_ACCELERATION:
        factor = min(1.0, 0.25 + tick * 0.06)
        density["cafeteria"] = noise(factor)
        activity["cafeteria"] = noise(factor * 0.9)
        density["hallway-a"] = noise(0.3 + tick * 0.02)

    elif scenario_id == ScenarioId.EXIT_BLOCKAGE:
        exit_tp["exit-main"] = max(0.05, 1.0 - tick * 0.12)
        density["exit-lobby"] = noise(min(1.0, 0.3 + tick * 0.08))
        density["cafeteria"] = noise(min(1.0, 0.35 + tick * 0.05))

    elif scenario_id == ScenarioId.AUDIO_STRESS_SIGNAL:
        audio["hallway-a"] = noise(min(1.0, 0.35 + tick * 0.07))
        density["hallway-a"] = noise(0.3)

    elif scenario_id == ScenarioId.MULTIMODAL_CONFLICT:
        activity["cafeteria"] = noise(0.15)
        audio["cafeteria"] = noise(min(1.0, 0.45 + tick * 0.08))
        density["cafeteria"] = noise(0.35)

    elif scenario_id == ScenarioId.EVACUATION_RECOMMENDATION:
        for zone_id in density:
            density[zone_id] = noise(min(1.0, 0.4 + tick * 0.07))
            activity[zone_id] = noise(min(1.0, 0.45 + tick * 0.06))
            audio[zone_id] = noise(min(1.0, 0.3 + tick * 0.05))

    flows = tuple(
        FlowEntity(entity_id=f"flow-{zone_id}", zone_id=zone_id, flow_rate=density[zone_id] * 100.0)
        for zone_id in density
    )

    return WorldState(
        tick=tick,
        elapsed_seconds=elapsed,
        zone_density=density,
        zone_activity=activity,
        zone_audio_stress=audio,
        exit_throughput=exit_tp,
        flow_entities=flows,
    )


__all__ = ["advance_world_state"]
