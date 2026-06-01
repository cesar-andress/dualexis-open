"""Evaluation layer — data models for planned empirical study.

Maps to DUALEXIS research methodology (Section methodology / evaluation plan).
No experimental results are stored or computed in v0.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class LayerMetadata:
    """Static descriptor for the evaluation support layer."""

    layer_id: str = "EVAL"
    name: str = "evaluation"
    processes_events_only: bool = True


EVALUATION_LAYER = LayerMetadata()


class EvaluationPhase(StrEnum):
    """Evaluation phases from the formal methodology."""

    PRIVACY_AUDIT = "privacy_audit"
    FUNCTIONAL_BENCHMARK = "functional_benchmark"
    FIELD_PILOT = "field_pilot"


class EvaluationMetric(StrEnum):
    """Pre-registered metrics aligned with framework layers."""

    BIOMETRIC_REJECTION_RATE = "biometric_rejection_rate"
    POST_TTL_MEDIA_COUNT = "post_ttl_media_count"
    FUSION_PRECISION = "fusion_precision"
    FUSION_RECALL = "fusion_recall"
    END_TO_END_LATENCY_P95 = "end_to_end_latency_p95"
    GROUNDING_ACCURACY = "grounding_accuracy"
    SA_COMPREHENSION_SCORE = "sa_comprehension_score"
    HUMAN_OVERRIDE_RATE = "human_override_rate"


class MetricTarget(BaseModel):
    """Declarative target for a single evaluation metric (no results)."""

    model_config = ConfigDict(frozen=True)

    metric: EvaluationMetric
    phase: EvaluationPhase
    target_description: str = Field(min_length=1, max_length=512)
    layer: str = Field(min_length=1, max_length=32, description="Framework layer L1-L6")


DEFAULT_METRIC_TARGETS: tuple[MetricTarget, ...] = (
    MetricTarget(
        metric=EvaluationMetric.BIOMETRIC_REJECTION_RATE,
        phase=EvaluationPhase.PRIVACY_AUDIT,
        target_description="100% rejection of forbidden biometric schema injections",
        layer="L1",
    ),
    MetricTarget(
        metric=EvaluationMetric.POST_TTL_MEDIA_COUNT,
        phase=EvaluationPhase.PRIVACY_AUDIT,
        target_description="Zero persistent raw media after buffer TTL",
        layer="L1",
    ),
    MetricTarget(
        metric=EvaluationMetric.FUSION_PRECISION,
        phase=EvaluationPhase.FUNCTIONAL_BENCHMARK,
        target_description="Pre-registered on synthetic annotated corpus",
        layer="L3",
    ),
    MetricTarget(
        metric=EvaluationMetric.GROUNDING_ACCURACY,
        phase=EvaluationPhase.FUNCTIONAL_BENCHMARK,
        target_description="Copilot references only input subgraph fields",
        layer="L5",
    ),
)

__all__ = [
    "DEFAULT_METRIC_TARGETS",
    "EVALUATION_LAYER",
    "EvaluationMetric",
    "EvaluationPhase",
    "LayerMetadata",
    "MetricTarget",
]
