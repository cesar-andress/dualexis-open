"""Semantic Safety State Graph service — evidence to state to graph transition."""

from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.scenario import ScenarioId
from dualexis.simulation.world import WorldState
from dualexis.sssg.evidence import (
    evidence_from_semantic_event,
    evidence_from_world_state,
    infer_safety_state_from_evidence,
)
from dualexis.sssg.explanations import (
    corroboration_note_from_evidence,
    format_state_transition_explanation,
)
from dualexis.sssg.models import (
    EvidenceRecord,
    SafetyState,
    SemanticSafetyStateGraph,
    StateSnapshotNode,
    StateTransition,
    StateTransitionEdge,
    TransitionEdgeKind,
)
from dualexis.sssg.transitions import resolve_transition


def _stable_sssg_uuid(seed: int, scenario_id: str, label: str, index: int) -> UUID:
    """Derive a deterministic UUID for reproducible SSSG traces."""
    return uuid5(NAMESPACE_URL, f"dualexis-sssg:{scenario_id}:{seed}:{label}:{index}")


class SemanticSafetyStateGraphService:
    """Maintains zone safety states and records transitions with typed edges."""

    def __init__(
        self,
        *,
        scenario_id: str = "",
        seed: int = 0,
    ) -> None:
        self._graph = SemanticSafetyStateGraph(scenario_id=scenario_id, seed=seed)
        self._id_seq = 0
        self._scenario_enum: ScenarioId | None = None
        try:
            self._scenario_enum = ScenarioId(scenario_id)
        except ValueError:
            self._scenario_enum = None

    @property
    def graph(self) -> SemanticSafetyStateGraph:
        return self._graph

    def _next_id(self, label: str) -> UUID:
        stable = _stable_sssg_uuid(
            self._graph.seed,
            self._graph.scenario_id,
            label,
            self._id_seq,
        )
        self._id_seq += 1
        return stable

    def bootstrap_zone(self, zone_id: str, *, tick: int, timestamp: datetime) -> None:
        if zone_id in self._graph.current_by_zone:
            return
        snapshot = StateSnapshotNode(
            snapshot_id=self._next_id(f"snapshot-{zone_id}-bootstrap"),
            zone_id=zone_id,
            state=SafetyState.NORMAL,
            tick=tick,
            timestamp=timestamp,
        )
        self._graph.snapshots.append(snapshot)
        self._graph.current_by_zone[zone_id] = SafetyState.NORMAL
        self._graph.last_snapshot_by_zone[zone_id] = snapshot.snapshot_id

    def ingest_world_evidence(
        self,
        state: WorldState,
        *,
        zone_id: str,
        timestamp: datetime,
        peer_zones: tuple[str, ...] = (),
    ) -> StateTransition | None:
        """Update safety state from anonymous world metrics."""
        self.bootstrap_zone(zone_id, tick=state.tick, timestamp=timestamp)
        evidence = evidence_from_world_state(state, zone_id=zone_id, timestamp=timestamp)
        return self._apply_evidence(
            zone_id,
            evidence,
            tick=state.tick,
            timestamp=timestamp,
            peer_zones=peer_zones,
        )

    def ingest_semantic_event(
        self,
        event: SemanticEvent,
        *,
        peer_zones: tuple[str, ...] = (),
    ) -> StateTransition | None:
        """Update safety state from a fused semantic event."""
        tick = int(event.metadata.get("tick", "0") or "0")
        self.bootstrap_zone(event.zone_id, tick=tick, timestamp=event.timestamp)
        evidence = (evidence_from_semantic_event(event),)
        return self._apply_evidence(
            event.zone_id,
            evidence,
            tick=tick,
            timestamp=event.timestamp,
            peer_zones=peer_zones,
        )

    def _apply_evidence(
        self,
        zone_id: str,
        evidence: tuple[EvidenceRecord, ...],
        *,
        tick: int,
        timestamp: datetime,
        peer_zones: tuple[str, ...],
    ) -> StateTransition | None:
        current = self._graph.current_state(zone_id)
        proposed = infer_safety_state_from_evidence(
            evidence,
            scenario_id=self._scenario_enum,
            zone_id=zone_id,
        )
        target = resolve_transition(current, proposed)
        if target == current:
            return None

        corroboration = corroboration_note_from_evidence(evidence, zone_id=zone_id)
        peer_notes: list[str] = []
        for peer in peer_zones:
            if peer == zone_id:
                continue
            peer_state = self._graph.current_state(peer)
            if peer_state not in {SafetyState.NORMAL, current}:
                peer_notes.append(
                    f"{peer} in {_state_label(peer_state)}"
                )

        prev_id = self._graph.last_snapshot_by_zone[zone_id]
        target_snapshot = StateSnapshotNode(
            snapshot_id=self._next_id(f"snapshot-{zone_id}-{tick}-{target.value}"),
            zone_id=zone_id,
            state=target,
            tick=tick,
            timestamp=timestamp,
        )
        self._graph.snapshots.append(target_snapshot)
        temporal_edge = StateTransitionEdge(
            edge_id=self._next_id(f"edge-temporal-{zone_id}-{tick}"),
            source_snapshot_id=prev_id,
            target_snapshot_id=target_snapshot.snapshot_id,
            kind=TransitionEdgeKind.TEMPORAL,
            description=f"Temporal progression in {zone_id}",
            evidence_ids=tuple(e.evidence_id for e in evidence),
        )
        self._graph.edges.append(temporal_edge)

        causal_edges: list[StateTransitionEdge] = []
        for record in evidence:
            causal = StateTransitionEdge(
                edge_id=self._next_id(
                    f"edge-causal-{zone_id}-{tick}-{record.evidence_id}",
                ),
                source_snapshot_id=prev_id,
                target_snapshot_id=target_snapshot.snapshot_id,
                kind=TransitionEdgeKind.CAUSAL,
                description=record.description,
                evidence_ids=(record.evidence_id,),
            )
            causal_edges.append(causal)
            self._graph.edges.append(causal)

        corroborative_ids: list = []
        if peer_notes:
            corr = StateTransitionEdge(
                edge_id=self._next_id(f"edge-corroborative-{zone_id}-{tick}"),
                source_snapshot_id=prev_id,
                target_snapshot_id=target_snapshot.snapshot_id,
                kind=TransitionEdgeKind.CORROBORATIVE,
                description="; ".join(peer_notes),
                evidence_ids=tuple(e.evidence_id for e in evidence),
            )
            corroborative_ids.append(corr.edge_id)
            self._graph.edges.append(corr)

        explanation = format_state_transition_explanation(
            StateTransition(
                zone_id=zone_id,
                tick=tick,
                timestamp=timestamp,
                from_state=current,
                to_state=target,
                evidence=evidence,
                corroboration_notes=corroboration,
                explanation="State transition pending narrative.",
            ),
            peer_zone_notes=tuple(peer_notes),
        )
        transition = StateTransition(
            transition_id=self._next_id(f"transition-{zone_id}-{tick}-{target.value}"),
            zone_id=zone_id,
            tick=tick,
            timestamp=timestamp,
            from_state=current,
            to_state=target,
            evidence=evidence,
            corroboration_notes=corroboration,
            explanation=explanation,
            temporal_edge_id=temporal_edge.edge_id,
            causal_edge_ids=tuple(e.edge_id for e in causal_edges),
            corroborative_edge_ids=tuple(corroborative_ids),
        )
        self._graph.transitions.append(transition)
        self._graph.current_by_zone[zone_id] = target
        self._graph.last_snapshot_by_zone[zone_id] = target_snapshot.snapshot_id
        return transition


def _state_label(state: SafetyState) -> str:
    return state.value.replace("_", " ")


__all__ = ["SemanticSafetyStateGraphService"]
