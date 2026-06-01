"""Leakage audit domain models for E2 ground-truth independence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ThresholdPredicate(BaseModel):
    """Normalized threshold comparison on a world metric."""

    model_config = ConfigDict(frozen=True)

    metric: str
    zone: str
    operator: str
    value: float
    scenario_id: str = ""
    component: str = ""
    label: str = ""


class LogicPredicate(BaseModel):
    """Normalized boolean condition (scenario/zone guards)."""

    model_config = ConfigDict(frozen=True)

    predicate_id: str
    scenario_id: str
    component: str
    expression: str


class ComponentSpec(BaseModel):
    """Extracted specification fragment for one simulator component."""

    model_config = ConfigDict(frozen=True)

    component_id: str
    variables: tuple[str, ...] = Field(default_factory=tuple)
    thresholds: tuple[ThresholdPredicate, ...] = Field(default_factory=tuple)
    logic_predicates: tuple[LogicPredicate, ...] = Field(default_factory=tuple)


class OverlapReport(BaseModel):
    """Pairwise and global overlap between E2 components."""

    model_config = ConfigDict(frozen=True)

    shared_variables_ratio: float = Field(ge=0.0, le=1.0)
    shared_threshold_ratio: float = Field(ge=0.0, le=1.0)
    shared_logic_ratio: float = Field(ge=0.0, le=1.0)
    variable_union_size: int = Field(ge=0)
    threshold_union_size: int = Field(ge=0)
    logic_union_size: int = Field(ge=0)


class IndependenceEstimates(BaseModel):
    """Three-layer independence scores in [0, 1] (1 = fully independent)."""

    model_config = ConfigDict(frozen=True)

    procedural_independence: float = Field(ge=0.0, le=1.0)
    semantic_independence: float = Field(ge=0.0, le=1.0)
    distributional_independence: float = Field(ge=0.0, le=1.0)


class LeakageAuditReport(BaseModel):
    """Full static + Monte Carlo leakage audit."""

    model_config = ConfigDict(frozen=True)

    leakage_score: float = Field(ge=0.0, le=1.0)
    overlap: OverlapReport
    independence: IndependenceEstimates
    monte_carlo_iterations: int = Field(ge=1)
    ground_truth_stability_mean: float = Field(ge=0.0, le=1.0)
    event_stability_mean: float = Field(ge=0.0, le=1.0)
    agreement_drift_mean: float = Field(ge=0.0, le=1.0)
    independence_disclosure: str = Field(min_length=1)
    dependency_graph_dot: str = ""
    per_scenario: dict[str, dict[str, float]] = Field(default_factory=dict)


__all__ = [
    "ComponentSpec",
    "IndependenceEstimates",
    "LeakageAuditReport",
    "LogicPredicate",
    "OverlapReport",
    "ThresholdPredicate",
]
