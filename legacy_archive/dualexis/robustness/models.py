"""Multiseed robustness audit models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class StabilityMetricKind(StrEnum):
    """Semantic stability dimensions under seed perturbation."""

    EVENT = "event_stability"
    STATE = "state_stability"
    RECOMMENDATION = "recommendation_stability"
    EXPLANATION = "explanation_stability"


class MetricDistribution(BaseModel):
    """Mean, dispersion, and coefficient of variation for one stability metric."""

    model_config = ConfigDict(frozen=True)

    metric: StabilityMetricKind
    mean: float
    std: float = Field(ge=0.0)
    coefficient_of_variation: float = Field(ge=0.0)
    per_seed_values: tuple[float, ...] = Field(default_factory=tuple)


class ScenarioRobustness(BaseModel):
    """Robustness audit for one scenario across N seeds."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1, max_length=64)
    seeds: tuple[int, ...]
    event_stability: float = Field(ge=0.0, le=1.0)
    state_stability: float = Field(ge=0.0, le=1.0)
    recommendation_stability: float = Field(ge=0.0, le=1.0)
    explanation_stability: float = Field(ge=0.0, le=1.0)
    distributions: tuple[MetricDistribution, ...] = Field(default_factory=tuple)
    per_seed_vs_reference: dict[int, dict[str, float]] = Field(default_factory=dict)


class RobustnessAuditReport(BaseModel):
    """Full multiseed robustness audit."""

    model_config = ConfigDict(frozen=True)

    audit_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    seeds: tuple[int, ...]
    scenarios: tuple[ScenarioRobustness, ...] = Field(default_factory=tuple)
    aggregate_distributions: tuple[MetricDistribution, ...] = Field(default_factory=tuple)
    robustness_score: float = Field(ge=0.0, le=1.0, description="Composite score R")
    disclaimer: str = Field(
        default=(
            "Multiseed robustness audit under stochastic world dynamics (synthetic harness). "
            "Stability is measured as signature agreement across seeds; not field variance."
        )
    )


__all__ = [
    "MetricDistribution",
    "RobustnessAuditReport",
    "ScenarioRobustness",
    "StabilityMetricKind",
]
