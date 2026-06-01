"""Unit tests for evaluation layer."""

from __future__ import annotations

import pytest

from dualexis.evaluation import EvaluationReport, PlaceholderEvaluationService


@pytest.mark.unit
def test_evaluation_registers_metrics_and_scaffold() -> None:
    service = PlaceholderEvaluationService()
    targets = service.registered_metrics()
    assert len(targets) >= 2
    report = service.evaluate("normal_flow", "dualexis_semantic", seed=42)
    assert isinstance(report, EvaluationReport)
    assert report.metrics.event_count >= 0.0
