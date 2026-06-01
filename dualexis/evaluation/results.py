"""Experiment result models for Q1-oriented DUALEXIS evaluation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

SCAFFOLD_DISCLAIMER = (
    "Scaffold experiment only; metrics are computed from synthetic simulation outputs "
    "and deterministic protocol executors. No empirical conclusions are implied."
)


class ExperimentMetrics(BaseModel):
    """Pre-registered metric bundle for a single protocol run."""

    model_config = ConfigDict(frozen=True)

    end_to_end_latency_ms: float = Field(ge=0.0)
    event_detection_accuracy: float = Field(ge=0.0, le=1.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0)
    false_negative_rate: float = Field(ge=0.0, le=1.0)
    time_to_recommendation_ms: float = Field(ge=0.0)
    explanation_completeness_score: float = Field(ge=0.0, le=1.0)
    human_review_compliance_rate: float = Field(ge=0.0, le=1.0)
    raw_data_retention_score: float = Field(ge=0.0, le=1.0)
    personal_data_exposure_score: float = Field(ge=0.0, le=1.0)
    privacy_violation_count: int = Field(ge=0)
    graph_update_latency_ms: float = Field(ge=0.0)

    @property
    def includes_privacy_metrics(self) -> bool:
        """Return True when all privacy-oriented metrics are present."""
        return (
            self.raw_data_retention_score >= 0.0
            and self.personal_data_exposure_score >= 0.0
            and self.privacy_violation_count >= 0
        )


class ExperimentReport(BaseModel):
    """Structured report for a single scenario/protocol experiment run."""

    model_config = ConfigDict(frozen=True)

    scenario_name: str = Field(min_length=1, max_length=64)
    protocol_id: str = Field(min_length=1, max_length=64)
    seed: int
    metrics: ExperimentMetrics
    generated_at: datetime
    notes: str = Field(default="", max_length=2048)


def format_experiment_summary(report: ExperimentReport) -> str:
    """Return a concise human-readable summary for CLI output."""
    metrics = report.metrics
    lines = [
        f"scenario={report.scenario_name} protocol={report.protocol_id} seed={report.seed}",
        f"end_to_end_latency_ms={metrics.end_to_end_latency_ms:.1f}",
        f"event_detection_accuracy={metrics.event_detection_accuracy:.4f}",
        f"false_positive_rate={metrics.false_positive_rate:.4f}",
        f"false_negative_rate={metrics.false_negative_rate:.4f}",
        f"time_to_recommendation_ms={metrics.time_to_recommendation_ms:.1f}",
        f"explanation_completeness_score={metrics.explanation_completeness_score:.4f}",
        f"human_review_compliance_rate={metrics.human_review_compliance_rate:.4f}",
        f"raw_data_retention_score={metrics.raw_data_retention_score:.4f}",
        f"personal_data_exposure_score={metrics.personal_data_exposure_score:.4f}",
        f"privacy_violation_count={metrics.privacy_violation_count}",
        f"graph_update_latency_ms={metrics.graph_update_latency_ms:.1f}",
    ]
    return "\n".join(lines)


__all__ = [
    "SCAFFOLD_DISCLAIMER",
    "ExperimentMetrics",
    "ExperimentReport",
    "format_experiment_summary",
]
