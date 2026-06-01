"""Causal Safety State Graph (CSSG) — explainable causal reasoning over safety states."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dualexis.sssg.models import (
    EvidenceRecord,
    SafetyState,
    StateSnapshotNode,
    StateTransition,
    StateTransitionEdge,
)


class CausalEdgeType(StrEnum):
    """Explicit causal edge semantics (CSSG)."""

    CONTRIBUTES_TO = "contributes_to"
    AGGRAVATES = "aggravates"
    MITIGATES = "mitigates"
    TRIGGERS = "triggers"


class CausalFactor(BaseModel):
    """A typed causal contributor linked to evidence."""

    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(min_length=1, max_length=64)
    edge_type: CausalEdgeType
    description: str = Field(min_length=1, max_length=512)
    evidence_id: str = Field(min_length=1, max_length=64)
    weight: float = Field(ge=0.0, le=1.0, default=1.0)


class CausalTypedEdge(BaseModel):
    """Directed causal edge between factors and/or states."""

    model_config = ConfigDict(frozen=True)

    edge_id: UUID = Field(default_factory=uuid4)
    edge_type: CausalEdgeType
    from_state: SafetyState
    to_state: SafetyState
    factor_id: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=512)


class CausalStateTransition(BaseModel):
    """Safety-state transition with mandatory causal attribution fields."""

    model_config = ConfigDict(frozen=True)

    transition_id: UUID
    zone_id: str = Field(min_length=1, max_length=64)
    tick: int = Field(ge=0)
    timestamp: datetime
    from_state: SafetyState
    to_state: SafetyState
    explanation: str = Field(min_length=1, max_length=2048)
    causal_factors: tuple[CausalFactor, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: tuple[EvidenceRecord, ...] = Field(min_length=1)
    alternative_explanations: tuple[str, ...] = Field(default_factory=tuple)
    typed_causal_edges: tuple[CausalTypedEdge, ...] = Field(default_factory=tuple)
    sssg_edge_ids: tuple[UUID, ...] = Field(default_factory=tuple)


class CausalStateTransitionTrace(BaseModel):
    """CSSG trace export (extends SSSG temporal structure with causal transitions)."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1, max_length=64)
    seed: int
    zone_ids: tuple[str, ...] = Field(default_factory=tuple)
    causal_transitions: tuple[CausalStateTransition, ...] = Field(default_factory=tuple)
    snapshots: tuple[StateSnapshotNode, ...] = Field(default_factory=tuple)
    edges: tuple[StateTransitionEdge, ...] = Field(default_factory=tuple)
    final_states: dict[str, SafetyState] = Field(default_factory=dict)

    @property
    def transitions(self) -> tuple[StateTransition, ...]:
        """SSSG-compatible transition view (for legacy metrics)."""
        return tuple(_to_sssg_transition(ct) for ct in self.causal_transitions)


class CausalSafetyStateGraph(BaseModel):
    """In-memory CSSG: SSSG backbone plus causal transition records."""

    model_config = ConfigDict(frozen=False)

    scenario_id: str = ""
    seed: int = 0
    causal_transitions: list[CausalStateTransition] = Field(default_factory=list)
    snapshots: list[StateSnapshotNode] = Field(default_factory=list)
    edges: list[StateTransitionEdge] = Field(default_factory=list)
    current_by_zone: dict[str, SafetyState] = Field(default_factory=dict)

    def to_trace(self) -> CausalStateTransitionTrace:
        return CausalStateTransitionTrace(
            scenario_id=self.scenario_id,
            seed=self.seed,
            zone_ids=tuple(sorted(self.current_by_zone)),
            causal_transitions=tuple(self.causal_transitions),
            snapshots=tuple(self.snapshots),
            edges=tuple(self.edges),
            final_states=dict(self.current_by_zone),
        )


def _to_sssg_transition(causal: CausalStateTransition) -> StateTransition:
    return StateTransition(
        transition_id=causal.transition_id,
        zone_id=causal.zone_id,
        tick=causal.tick,
        timestamp=causal.timestamp,
        from_state=causal.from_state,
        to_state=causal.to_state,
        evidence=causal.supporting_evidence,
        explanation=causal.explanation,
        causal_edge_ids=causal.sssg_edge_ids,
    )


__all__ = [
    "CausalEdgeType",
    "CausalFactor",
    "CausalSafetyStateGraph",
    "CausalStateTransition",
    "CausalStateTransitionTrace",
    "CausalTypedEdge",
]
