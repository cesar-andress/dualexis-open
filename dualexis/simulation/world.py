"""Confined-space world model for DUALEXIS simulation.

Models G = (V, E) with zones, exits, and anonymous flow entities (not identities).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ZoneKind(StrEnum):
    """Zone classification in the simulated confined space."""

    CORRIDOR = "corridor"
    OPEN_AREA = "open_area"
    EXIT_LOBBY = "exit_lobby"


class ZoneNode(BaseModel):
    """A zone node v in V — spatial region, not a person."""

    model_config = ConfigDict(frozen=True)

    zone_id: str = Field(min_length=1, max_length=64)
    zone_label: str = Field(min_length=1, max_length=128)
    kind: ZoneKind = ZoneKind.CORRIDOR


class ExitNode(BaseModel):
    """An exit attachment in the confined-space graph."""

    model_config = ConfigDict(frozen=True)

    exit_id: str = Field(min_length=1, max_length=64)
    zone_id: str = Field(min_length=1, max_length=64)
    is_emergency: bool = True
    throughput: float = Field(default=1.0, ge=0.0, le=10.0)


class FlowEntity(BaseModel):
    """Anonymous flow bundle — aggregate movement, not an identified individual."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=64)
    zone_id: str = Field(min_length=1, max_length=64)
    flow_rate: float = Field(ge=0.0, le=1000.0, description="Anonymous flow units per tick")


@dataclass
class ConfinedSpaceGraph:
    """Static topology G = (V, E) for the simulated site."""

    location_id: str
    zones: tuple[ZoneNode, ...]
    exits: tuple[ExitNode, ...]
    edges: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def adjacent_zones(self, zone_id: str) -> tuple[str, ...]:
        from_a = {b for a, b in self.edges if a == zone_id}
        from_b = {a for a, b in self.edges if b == zone_id}
        return tuple(sorted(from_a | from_b))


@dataclass
class WorldState:
    """Dynamic simulation state at discrete tick t."""

    tick: int
    elapsed_seconds: float
    zone_density: dict[str, float]
    zone_activity: dict[str, float]
    zone_audio_stress: dict[str, float]
    exit_throughput: dict[str, float]
    flow_entities: tuple[FlowEntity, ...]


def build_default_world(*, location_id: str = "sim-school-north") -> ConfinedSpaceGraph:
    """Build a reproducible three-zone confined-space graph with two exits."""
    zones = (
        ZoneNode(zone_id="hallway-a", zone_label="Hallway A", kind=ZoneKind.CORRIDOR),
        ZoneNode(zone_id="cafeteria", zone_label="Cafeteria", kind=ZoneKind.OPEN_AREA),
        ZoneNode(zone_id="exit-lobby", zone_label="Exit Lobby", kind=ZoneKind.EXIT_LOBBY),
    )
    exits = (
        ExitNode(exit_id="exit-north", zone_id="hallway-a", throughput=1.0),
        ExitNode(exit_id="exit-main", zone_id="exit-lobby", throughput=1.0),
    )
    edges = frozenset(
        {
            ("hallway-a", "cafeteria"),
            ("cafeteria", "exit-lobby"),
        }
    )
    return ConfinedSpaceGraph(
        location_id=location_id,
        zones=zones,
        exits=exits,
        edges=edges,
    )


def initial_world_state(graph: ConfinedSpaceGraph) -> WorldState:
    """Create baseline world state for tick 0."""
    zone_ids = [z.zone_id for z in graph.zones]
    base_density = {z: 0.2 for z in zone_ids}
    base_activity = {z: 0.15 for z in zone_ids}
    base_audio = {z: 0.1 for z in zone_ids}
    exit_tp = {e.exit_id: e.throughput for e in graph.exits}
    flows = tuple(
        FlowEntity(
            entity_id=f"flow-{z}",
            zone_id=z,
            flow_rate=base_density[z] * 10.0,
        )
        for z in zone_ids
    )
    return WorldState(
        tick=0,
        elapsed_seconds=0.0,
        zone_density=base_density,
        zone_activity=base_activity,
        zone_audio_stress=base_audio,
        exit_throughput=exit_tp,
        flow_entities=flows,
    )
