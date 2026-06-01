"""Formal Human-AI governance state machine models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dualexis.governance.models import GovernanceState, OperatorAction, OperatorProfile


class GovernanceMacroState(StrEnum):
    """Top-level governance phases for high-risk decision support."""

    AI_RECOMMENDATION = "ai_recommendation"
    HUMAN_REVIEW = "human_review"
    INSTITUTIONAL_ESCALATION = "institutional_escalation"


class GovernanceTransitionSymbol(StrEnum):
    """Transition alphabet Σ for the governance FSM."""

    ISSUE = "issue"  # τ_issue: publish recommendation to review queue
    ACCEPT = "accept"
    OVERRIDE = "override"
    DISMISS = "dismiss"
    ESCALATE = "escalate"
    CLOSE = "close"  # τ_close: institutional disposition recorded


class GovernanceTransitionDef(BaseModel):
    """One tuple (s, σ, s') in the transition relation."""

    model_config = ConfigDict(frozen=True)

    from_state: GovernanceMacroState
    symbol: GovernanceTransitionSymbol
    to_state: GovernanceMacroState
    guard: str = Field(
        default="true",
        description="Predicate name g(s,σ) documented in the formal model.",
    )


class GovernanceTraceStep(BaseModel):
    """Single step in a governance decision trace."""

    model_config = ConfigDict(frozen=True)

    step_index: int = Field(ge=0)
    from_state: GovernanceMacroState
    symbol: GovernanceTransitionSymbol
    to_state: GovernanceMacroState
    timestamp: datetime
    micro_state: GovernanceState | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class GovernanceDecisionTrace(BaseModel):
    """Auditable trace for one recommendation disposition."""

    model_config = ConfigDict(frozen=True)

    trace_id: UUID = Field(default_factory=uuid4)
    case_id: str
    scenario_id: str
    zone_id: str
    profile: OperatorProfile
    steps: tuple[GovernanceTraceStep, ...] = Field(min_length=1)
    terminal_macro_state: GovernanceMacroState
    ai_correct: bool
    requires_escalation: bool
    policy_compliant: bool
    trace_complete: bool = True


class GovernanceGraphEdge(BaseModel):
    """Weighted edge in the governance graph."""

    model_config = ConfigDict(frozen=True)

    from_state: GovernanceMacroState
    to_state: GovernanceMacroState
    symbol: GovernanceTransitionSymbol
    probability: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=0, default=0)


class GovernanceGraph(BaseModel):
    """Formal governance graph G = (V, E) with transition probabilities."""

    model_config = ConfigDict(frozen=True)

    nodes: tuple[GovernanceMacroState, ...]
    edges: tuple[GovernanceGraphEdge, ...]
    transition_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    transition_relation: tuple[GovernanceTransitionDef, ...] = Field(default_factory=tuple)
    dot: str = ""


class FormalGovernanceMetrics(BaseModel):
    """Formal governance audit metrics in [0, 1]."""

    model_config = ConfigDict(frozen=True)

    governance_compliance_score: float = Field(ge=0.0, le=1.0)
    institutional_reliance_index: float = Field(ge=0.0, le=1.0)
    human_override_resilience: float = Field(ge=0.0, le=1.0)
    decision_traceability: float = Field(ge=0.0, le=1.0)


class GovernanceAuditReport(BaseModel):
    """Formal Human-AI governance audit for high-risk decision support."""

    model_config = ConfigDict(frozen=True)

    audit_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    framework_title: str = Field(min_length=1)
    graph: GovernanceGraph
    metrics: FormalGovernanceMetrics
    traces: tuple[GovernanceDecisionTrace, ...] = Field(default_factory=tuple)
    trace_count: int = Field(ge=0)
    simulation_iterations: int = Field(ge=1)
    disclaimer: str = Field(min_length=1)


FORMAL_FRAMEWORK_TITLE = (
    "Formal Human-AI Governance State Machine for High-Risk Decision Support Systems"
)


__all__ = [
    "FORMAL_FRAMEWORK_TITLE",
    "FormalGovernanceMetrics",
    "GovernanceAuditReport",
    "GovernanceDecisionTrace",
    "GovernanceGraph",
    "GovernanceGraphEdge",
    "GovernanceMacroState",
    "GovernanceTraceStep",
    "GovernanceTransitionDef",
    "GovernanceTransitionSymbol",
]
