"""Evaluation layer — placeholder service (metrics registry + scaffold runner)."""

from __future__ import annotations

from dualexis.evaluation.interfaces import EvaluationService
from dualexis.evaluation.models import DEFAULT_METRIC_TARGETS, EvaluationMetric, MetricTarget
from dualexis.evaluation.report import EvaluationReport, run_evaluation

_IMPLEMENTED_METRICS = frozenset(
    {
        EvaluationMetric.FUSION_PRECISION,
        EvaluationMetric.FUSION_RECALL,
        EvaluationMetric.END_TO_END_LATENCY_P95,
    }
)


class PlaceholderEvaluationService(EvaluationService):
    """Registers evaluation metrics and exposes the scaffold runner."""

    def __init__(self, targets: tuple[MetricTarget, ...] | None = None) -> None:
        self._targets = targets or DEFAULT_METRIC_TARGETS

    def registered_metrics(self) -> tuple[MetricTarget, ...]:
        return self._targets

    def is_implemented(self, metric: EvaluationMetric) -> bool:
        return metric in _IMPLEMENTED_METRICS

    def evaluate(
        self,
        scenario_name: str,
        baseline_name: str,
        *,
        seed: int = 42,
    ) -> EvaluationReport:
        """Run the reproducible evaluation scaffold for a scenario/baseline pair."""
        return run_evaluation(scenario_name, baseline_name, seed=seed)
