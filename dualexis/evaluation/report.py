"""Evaluation report generation for DUALEXIS benchmarks."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from dualexis.evaluation.baselines import Baseline, UnknownBaselineError, get_baseline
from dualexis.evaluation.metrics import EvaluationMetricSet, compute_metrics
from dualexis.evaluation.results import SCAFFOLD_DISCLAIMER
from dualexis.simulation.runner import run_scenario
from dualexis.simulation.scenario import UnknownScenarioError


class EvaluationReport(BaseModel):
    """Structured report for a single scenario/baseline evaluation run."""

    model_config = ConfigDict(frozen=True)

    scenario_name: str = Field(min_length=1, max_length=64)
    baseline_name: str = Field(min_length=1, max_length=64)
    seed: int
    metrics: EvaluationMetricSet
    generated_at: datetime
    notes: str = Field(default="", max_length=2048)


def run_evaluation(
    scenario_name: str,
    baseline_name: str,
    *,
    seed: int = 42,
    baseline: Baseline | None = None,
    notes: str = "",
) -> EvaluationReport:
    """Run simulation + baseline and return a reproducible evaluation report."""
    simulation = run_scenario(scenario_name, seed=seed)
    resolved_baseline = baseline or get_baseline(baseline_name)
    output = resolved_baseline.run(simulation)
    metrics = compute_metrics(output, simulation.ground_truth)

    default_notes = SCAFFOLD_DISCLAIMER
    merged_notes = notes.strip() or default_notes

    return EvaluationReport(
        scenario_name=scenario_name,
        baseline_name=resolved_baseline.name,
        seed=seed,
        metrics=metrics,
        generated_at=datetime.now(tz=UTC),
        notes=merged_notes,
    )


def format_report_summary(report: EvaluationReport) -> str:
    """Return a concise human-readable summary for CLI output."""
    metrics = report.metrics
    lines = [
        f"scenario={report.scenario_name} baseline={report.baseline_name} seed={report.seed}",
        f"event_count={metrics.event_count:.0f}",
        f"average_confidence={metrics.average_confidence:.4f}",
        f"high_severity_rate={metrics.high_severity_rate:.4f}",
        f"false_positive_rate={metrics.false_positive_rate:.4f}",
        f"false_negative_rate={metrics.false_negative_rate:.4f}",
        f"time_to_recommendation_ms={metrics.time_to_recommendation_ms:.1f}",
        f"raw_media_retention_score={metrics.raw_media_retention_score:.4f}",
        f"personal_data_exposure_score={metrics.personal_data_exposure_score:.4f}",
        f"human_review_compliance_rate={metrics.human_review_compliance_rate:.4f}",
    ]
    return "\n".join(lines)


__all__ = [
    "EvaluationReport",
    "UnknownBaselineError",
    "UnknownScenarioError",
    "format_report_summary",
    "run_evaluation",
]
