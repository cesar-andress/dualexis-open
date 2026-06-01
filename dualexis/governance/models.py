"""Formal Human-AI governance models for safety decision support."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dualexis.orchestration.models import SeverityLevel


class GovernanceState(StrEnum):
    """Lifecycle state for a governance review item."""

    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    OVERRIDDEN = "overridden"
    ESCALATED = "escalated"
    DISMISSED = "dismissed"


class OperatorProfile(StrEnum):
    """Simulated operator disposition toward AI recommendations."""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class OperatorAction(StrEnum):
    """Operator disposition applied to a pending review."""

    ACCEPT = "accept"
    OVERRIDE = "override"
    ESCALATE = "escalate"
    DISMISS = "dismiss"


ACTION_TO_STATE: dict[OperatorAction, GovernanceState] = {
    OperatorAction.ACCEPT: GovernanceState.REVIEWED,
    OperatorAction.OVERRIDE: GovernanceState.OVERRIDDEN,
    OperatorAction.ESCALATE: GovernanceState.ESCALATED,
    OperatorAction.DISMISS: GovernanceState.DISMISSED,
}


class GovernanceReviewCase(BaseModel):
    """A recommendation awaiting formal governance review."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1, max_length=64)
    scenario_id: str = Field(min_length=1, max_length=64)
    zone_id: str = Field(min_length=1, max_length=64)
    severity: SeverityLevel
    ai_action: str = Field(min_length=1, max_length=256)
    oracle_action: str = Field(min_length=1, max_length=256)
    ai_confidence: float = Field(ge=0.0, le=1.0)
    ai_correct: bool
    requires_escalation: bool
    created_at: datetime


class OperatorDecision(BaseModel):
    """Recorded operator action on a governance case."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1, max_length=64)
    profile: OperatorProfile
    prior_state: GovernanceState = GovernanceState.PENDING_REVIEW
    action: OperatorAction
    resulting_state: GovernanceState
    latency_seconds: float = Field(ge=0.0)
    decided_at: datetime


class BiasRiskMetrics(BaseModel):
    """Human-AI reliance risk indicators in [0, 1]."""

    model_config = ConfigDict(frozen=True)

    automation_bias_risk: float = Field(ge=0.0, le=1.0)
    under_reliance_risk: float = Field(ge=0.0, le=1.0)
    over_reliance_risk: float = Field(ge=0.0, le=1.0)


class ProfileGovernanceMetrics(BaseModel):
    """Aggregate governance KPIs for one operator profile."""

    model_config = ConfigDict(frozen=True)

    profile: OperatorProfile
    decision_count: int = Field(ge=0)
    acceptance_rate: float = Field(ge=0.0, le=1.0)
    override_rate: float = Field(ge=0.0, le=1.0)
    escalation_rate: float = Field(ge=0.0, le=1.0)
    dismissal_rate: float = Field(ge=0.0, le=1.0)
    mean_review_latency_seconds: float = Field(ge=0.0)
    bias_risks: BiasRiskMetrics


class GovernanceEvaluationReport(BaseModel):
    """Full governance simulation and export summary."""

    model_config = ConfigDict(frozen=True)

    contribution_title: str = Field(min_length=1)
    simulation_iterations: int = Field(ge=1)
    case_pool_size: int = Field(ge=1)
    profile_metrics: tuple[ProfileGovernanceMetrics, ...]
    dependency_graph_dot: str = Field(min_length=1)
    decisions_csv: str = Field(min_length=1)


__all__ = [
    "ACTION_TO_STATE",
    "BiasRiskMetrics",
    "GovernanceEvaluationReport",
    "GovernanceReviewCase",
    "GovernanceState",
    "OperatorAction",
    "OperatorDecision",
    "OperatorProfile",
    "ProfileGovernanceMetrics",
]
