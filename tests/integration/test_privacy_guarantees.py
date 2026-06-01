"""Integration tests for privacy guarantees in experimental runs."""

from __future__ import annotations

import pytest

from dualexis.evaluation import ExperimentProtocolId, run_experiment
from dualexis.pipeline import run_pipeline


@pytest.mark.integration
@pytest.mark.parametrize("protocol", [protocol.value for protocol in ExperimentProtocolId])
def test_experiment_reports_include_privacy_metrics(protocol: str) -> None:
    report = run_experiment("exit_blockage", protocol, seed=42)
    metrics = report.metrics
    assert metrics.includes_privacy_metrics
    assert metrics.raw_data_retention_score >= 0.0
    assert metrics.personal_data_exposure_score >= 0.0
    assert metrics.privacy_violation_count >= 0


@pytest.mark.integration
def test_full_pipeline_privacy_report_no_raw_media() -> None:
    output = run_pipeline("exit_blockage", seed=42)
    assert output.privacy_report.raw_media_persisted is False
    assert output.privacy_report.raw_media_bytes_persisted == 0
    assert output.privacy_report.policy_compliant is True


@pytest.mark.integration
def test_full_pipeline_experiment_zero_privacy_violations() -> None:
    report = run_experiment("exit_blockage", "dualexis_full_pipeline", seed=42)
    assert report.metrics.privacy_violation_count == 0
    assert report.metrics.raw_data_retention_score == 1.0
    assert report.metrics.personal_data_exposure_score == 0.0
