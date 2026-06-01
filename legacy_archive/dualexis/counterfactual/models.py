"""Counterfactual safety reasoning models (SSSG-backed)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dualexis.orchestration.models import SeverityLevel
from dualexis.sssg.models import SafetyState


class CounterfactualInterventionKind(StrEnum):
    """Standard perturbations for what-if analysis."""

    DENSITY_BELOW_THRESHOLD = "density_below_threshold"
    EXIT_THROUGHPUT_RECOVERED = "exit_throughput_recovered"
    AUDIO_STRESS_CLEARED = "audio_stress_cleared"


class CounterfactualScenario(BaseModel):
    """A single what-if intervention and its inferred outcome."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1, max_length=64)
    intervention: CounterfactualInterventionKind
    hypothesis: str = Field(min_length=1, max_length=256)
    question: str = Field(
        min_length=1,
        max_length=256,
        description="Operator-facing form: What would have happened if...",
    )
    perturbed_metrics: dict[str, float] = Field(default_factory=dict)
    counterfactual_state: SafetyState
    counterfactual_action: str = Field(min_length=1, max_length=128)
    would_avoid_recommendation: bool
    explanation: str = Field(min_length=1, max_length=2048)
    confidence: float = Field(ge=0.0, le=1.0)


class CounterfactualRecommendation(BaseModel):
    """Counterfactual analysis attached to one orchestration recommendation."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: UUID
    scenario_id: str = Field(min_length=1, max_length=64)
    seed: int
    zone_id: str = Field(min_length=1, max_length=64)
    tick: int = Field(ge=0)
    baseline_state: SafetyState
    baseline_action: str = Field(min_length=1, max_length=128)
    baseline_severity: SeverityLevel
    baseline_rationale: str = Field(min_length=1, max_length=2048)
    counterfactuals: tuple[CounterfactualScenario, ...] = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=4096)


class CounterfactualTrace(BaseModel):
    """Full counterfactual run for one scenario/seed."""

    model_config = ConfigDict(frozen=True)

    trace_id: UUID = Field(default_factory=uuid4)
    scenario_id: str = Field(min_length=1, max_length=64)
    seed: int
    generated_at: datetime
    recommendations: tuple[CounterfactualRecommendation, ...] = Field(default_factory=tuple)
    counterfactual_consistency: float = Field(ge=0.0, le=1.0)
    counterfactual_stability: float = Field(ge=0.0, le=1.0, default=1.0)
    counterfactual_explanation_coverage: float = Field(ge=0.0, le=1.0)


class CounterfactualEvaluationReport(BaseModel):
    """Aggregate counterfactual metrics across scenarios."""

    model_config = ConfigDict(frozen=True)

    traces: tuple[CounterfactualTrace, ...] = Field(default_factory=tuple)
    mean_counterfactual_consistency: float = Field(ge=0.0, le=1.0)
    mean_counterfactual_stability: float = Field(ge=0.0, le=1.0)
    mean_counterfactual_explanation_coverage: float = Field(ge=0.0, le=1.0)
    recommendation_count: int = Field(ge=0)


__all__ = [
    "CounterfactualEvaluationReport",
    "CounterfactualInterventionKind",
    "CounterfactualRecommendation",
    "CounterfactualScenario",
    "CounterfactualTrace",
]
