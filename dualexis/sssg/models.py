"""Semantic Safety State Graph (SSSG) domain models.

Architecture: evidence -> safety state -> graph transition -> recommendation.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SafetyState(StrEnum):
    """Zone-scoped semantic safety state (occupant-agnostic)."""

    NORMAL = "normal"
    CROWDING_RISK = "crowding_risk"
    EXIT_IMPAIRMENT = "exit_impairment"
    AUDIO_STRESS = "audio_stress"
    MULTI_MODAL_CONFLICT = "multi_modal_conflict"
    EVACUATION_CANDIDATE = "evacuation_candidate"


class TransitionEdgeKind(StrEnum):
    """Edge semantics in the temporal safety state graph."""

    CAUSAL = "causal"
    TEMPORAL = "temporal"
    CORROBORATIVE = "corroborative"


class EvidenceKind(StrEnum):
    """Typed evidence feeding state inference."""

    ZONE_DENSITY = "zone_density"
    ZONE_ACTIVITY = "zone_activity"
    ZONE_AUDIO = "zone_audio"
    EXIT_THROUGHPUT = "exit_throughput"
    SEMANTIC_EVENT = "semantic_event"
    FUSION = "fusion"


class EvidenceRecord(BaseModel):
    """Anonymous observation supporting a state update."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(min_length=1, max_length=64)
    kind: EvidenceKind
    zone_id: str = Field(min_length=1, max_length=64)
    tick: int = Field(ge=0)
    timestamp: datetime
    metric_value: float | None = None
    description: str = Field(default="", max_length=512)
    source_event_id: UUID | None = None


class StateSnapshotNode(BaseModel):
    """Graph vertex: a safety state held by a zone at an instant."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: UUID = Field(default_factory=uuid4)
    zone_id: str = Field(min_length=1, max_length=64)
    state: SafetyState
    tick: int = Field(ge=0)
    timestamp: datetime


class StateTransitionEdge(BaseModel):
    """Directed edge between state snapshots."""

    model_config = ConfigDict(frozen=True)

    edge_id: UUID = Field(default_factory=uuid4)
    source_snapshot_id: UUID
    target_snapshot_id: UUID
    kind: TransitionEdgeKind
    description: str = Field(default="", max_length=512)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class StateTransition(BaseModel):
    """Recorded change of safety state for one zone."""

    model_config = ConfigDict(frozen=True)

    transition_id: UUID = Field(default_factory=uuid4)
    zone_id: str = Field(min_length=1, max_length=64)
    tick: int = Field(ge=0)
    timestamp: datetime
    from_state: SafetyState
    to_state: SafetyState
    evidence: tuple[EvidenceRecord, ...] = Field(default_factory=tuple)
    corroboration_notes: tuple[str, ...] = Field(default_factory=tuple)
    explanation: str = Field(min_length=1, max_length=2048)
    causal_edge_ids: tuple[UUID, ...] = Field(default_factory=tuple)
    temporal_edge_id: UUID | None = None
    corroborative_edge_ids: tuple[UUID, ...] = Field(default_factory=tuple)


class StateTransitionTrace(BaseModel):
    """Full trace export for one pipeline or simulation run."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1, max_length=64)
    seed: int
    zone_ids: tuple[str, ...] = Field(default_factory=tuple)
    transitions: tuple[StateTransition, ...] = Field(default_factory=tuple)
    snapshots: tuple[StateSnapshotNode, ...] = Field(default_factory=tuple)
    edges: tuple[StateTransitionEdge, ...] = Field(default_factory=tuple)
    final_states: dict[str, SafetyState] = Field(default_factory=dict)


class SemanticSafetyStateGraph(BaseModel):
    """In-memory temporal graph of safety states and typed edges."""

    model_config = ConfigDict(frozen=False)

    scenario_id: str = ""
    seed: int = 0
    snapshots: list[StateSnapshotNode] = Field(default_factory=list)
    edges: list[StateTransitionEdge] = Field(default_factory=list)
    transitions: list[StateTransition] = Field(default_factory=list)
    current_by_zone: dict[str, SafetyState] = Field(default_factory=dict)
    last_snapshot_by_zone: dict[str, UUID] = Field(default_factory=dict)

    def current_state(self, zone_id: str) -> SafetyState:
        return self.current_by_zone.get(zone_id, SafetyState.NORMAL)

    def to_trace(self) -> StateTransitionTrace:
        return StateTransitionTrace(
            scenario_id=self.scenario_id,
            seed=self.seed,
            zone_ids=tuple(sorted(self.current_by_zone)),
            transitions=tuple(self.transitions),
            snapshots=tuple(self.snapshots),
            edges=tuple(self.edges),
            final_states=dict(self.current_by_zone),
        )


__all__ = [
    "EvidenceKind",
    "EvidenceRecord",
    "SafetyState",
    "SemanticSafetyStateGraph",
    "StateSnapshotNode",
    "StateTransition",
    "StateTransitionEdge",
    "StateTransitionTrace",
    "TransitionEdgeKind",
]
