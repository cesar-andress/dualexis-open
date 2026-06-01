"""Institutional Memory Graph (IMG) domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class MemoryNodeKind(StrEnum):
    """Vertex kinds in the institutional memory graph."""

    SCENARIO = "scenario"
    GOVERNANCE_STATE = "governance_state"
    OPERATOR_ACTION = "operator_action"
    PATTERN = "pattern"


class MemoryEdgeKind(StrEnum):
    """Edge semantics in IMG."""

    OBSERVED_TRANSITION = "observed_transition"
    PATTERN_SUPPORT = "pattern_support"
    ESCALATION_CHAIN = "escalation_chain"
    NEAR_MISS_LINK = "near_miss_link"


class GovernancePattern(BaseModel):
    """Recurring historical governance disposition pattern."""

    model_config = ConfigDict(frozen=True)

    pattern_id: str
    scenario_id: str
    severity: str
    ai_action: str
    symbol_sequence: tuple[str, ...]
    terminal_state: str
    support_count: int = Field(ge=1)
    support_ratio: float = Field(ge=0.0, le=1.0)
    policy_compliance_rate: float = Field(ge=0.0, le=1.0)


class NearMissPattern(BaseModel):
    """Near-miss: high-risk disposition that narrowly avoided policy failure."""

    model_config = ConfigDict(frozen=True)

    pattern_id: str
    scenario_id: str
    zone_id: str
    near_miss_type: str
    description: str = Field(min_length=1, max_length=512)
    occurrence_count: int = Field(ge=1)
    ai_correct: bool
    operator_action: str
    policy_compliant: bool


class EscalationChainPattern(BaseModel):
    """Recurrent institutional escalation chain."""

    model_config = ConfigDict(frozen=True)

    pattern_id: str
    chain: tuple[str, ...] = Field(min_length=2)
    occurrence_count: int = Field(ge=1)
    support_ratio: float = Field(ge=0.0, le=1.0)
    scenarios: tuple[str, ...] = Field(default_factory=tuple)


class OverridePattern(BaseModel):
    """Frequent operator override of AI advice."""

    model_config = ConfigDict(frozen=True)

    pattern_id: str
    scenario_id: str
    ai_action: str
    severity: str
    occurrence_count: int = Field(ge=1)
    support_ratio: float = Field(ge=0.0, le=1.0)
    corrected_ai_incorrect: int = Field(ge=0)


class MemoryGraphNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    kind: MemoryNodeKind
    label: str = Field(min_length=1, max_length=128)


class MemoryGraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_id: str
    to_id: str
    kind: MemoryEdgeKind
    weight: float = Field(ge=0.0)
    count: int = Field(ge=0, default=0)


class InstitutionalMemoryGraph(BaseModel):
    """Organizational memory aggregated from historical TSGG governance traces."""

    model_config = ConfigDict(frozen=True)

    graph_id: UUID = Field(default_factory=uuid4)
    nodes: tuple[MemoryGraphNode, ...] = Field(default_factory=tuple)
    edges: tuple[MemoryGraphEdge, ...] = Field(default_factory=tuple)
    governance_patterns: tuple[GovernancePattern, ...] = Field(default_factory=tuple)
    near_miss_patterns: tuple[NearMissPattern, ...] = Field(default_factory=tuple)
    escalation_chains: tuple[EscalationChainPattern, ...] = Field(default_factory=tuple)
    override_patterns: tuple[OverridePattern, ...] = Field(default_factory=tuple)
    trace_count: int = Field(ge=0)
    dot: str = ""


class InstitutionalMemoryMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    memory_coverage: float = Field(ge=0.0, le=1.0)
    pattern_recurrence: float = Field(ge=0.0, le=1.0)
    governance_learning_index: float = Field(ge=0.0, le=1.0)


class InstitutionalMemoryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    graph: InstitutionalMemoryGraph
    metrics: InstitutionalMemoryMetrics
    disclaimer: str = Field(min_length=1)


IMG_DISCLAIMER = (
    "Institutional Memory Graphs mine synthetic TSGG governance histories for organizational "
    "learning descriptors. Patterns support safety decision-support design review, not "
    "automated enforcement in deployed systems."
)


__all__ = [
    "IMG_DISCLAIMER",
    "EscalationChainPattern",
    "GovernancePattern",
    "InstitutionalMemoryGraph",
    "InstitutionalMemoryMetrics",
    "InstitutionalMemoryReport",
    "MemoryEdgeKind",
    "MemoryGraphEdge",
    "MemoryGraphNode",
    "MemoryNodeKind",
    "NearMissPattern",
    "OverridePattern",
]
