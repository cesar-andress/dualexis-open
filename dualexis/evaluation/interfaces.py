"""Evaluation layer — service interfaces.

Maps to DUALEXIS research methodology; records metric definitions only in v0.1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dualexis.evaluation.models import EvaluationMetric, MetricTarget


class EvaluationService(ABC):
    """Registry and runner for planned evaluation protocols."""

    @abstractmethod
    def registered_metrics(self) -> tuple[MetricTarget, ...]:
        """Return pre-registered metric targets."""

    @abstractmethod
    def is_implemented(self, metric: EvaluationMetric) -> bool:
        """Return whether an metric runner is implemented."""
