"""Causal Safety State Graph service — SSSG backbone with causal attribution."""

from __future__ import annotations

from datetime import datetime

from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.world import WorldState
from dualexis.sssg.models import StateTransition
from dualexis.sssg.service import SemanticSafetyStateGraphService
from dualexis.cssg.causal_factors import enrich_transition
from dualexis.cssg.models import CausalSafetyStateGraph, CausalStateTransition


class CausalSafetyStateGraphService:
    """Wraps SSSG ingestion and records CSSG causal transitions."""

    def __init__(self, *, scenario_id: str = "", seed: int = 0) -> None:
        self._sssg = SemanticSafetyStateGraphService(scenario_id=scenario_id, seed=seed)
        self._graph = CausalSafetyStateGraph(scenario_id=scenario_id, seed=seed)

    @property
    def sssg(self) -> SemanticSafetyStateGraphService:
        return self._sssg

    def ingest_world_evidence(
        self,
        state: WorldState,
        *,
        zone_id: str,
        timestamp: datetime,
        peer_zones: tuple[str, ...] = (),
    ) -> CausalStateTransition | None:
        transition = self._sssg.ingest_world_evidence(
            state,
            zone_id=zone_id,
            timestamp=timestamp,
            peer_zones=peer_zones,
        )
        return self._record_causal(transition)

    def ingest_semantic_event(
        self,
        event: SemanticEvent,
        *,
        peer_zones: tuple[str, ...] = (),
    ) -> CausalStateTransition | None:
        transition = self._sssg.ingest_semantic_event(event, peer_zones=peer_zones)
        return self._record_causal(transition)

    def _record_causal(self, transition: StateTransition | None) -> CausalStateTransition | None:
        if transition is None:
            return None
        causal = enrich_transition(transition)
        self._graph.causal_transitions.append(causal)
        self._sync_backbone()
        return causal

    def _sync_backbone(self) -> None:
        backbone = self._sssg.graph
        self._graph.snapshots = backbone.snapshots
        self._graph.edges = backbone.edges
        self._graph.current_by_zone = dict(backbone.current_by_zone)

    def find_root_causes(self, zone_id: str, tick: int):
        from dualexis.cssg.paths import find_root_causes

        return find_root_causes(self._graph.to_trace(), zone_id, tick)


__all__ = ["CausalSafetyStateGraphService"]
