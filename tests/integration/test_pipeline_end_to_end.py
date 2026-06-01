"""Integration tests for end-to-end DUALEXIS pipeline execution."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from dualexis.cli import app
from dualexis.pipeline import run_pipeline

runner = CliRunner()


@pytest.mark.integration
def test_pipeline_integration_exit_blockage() -> None:
    output = run_pipeline("exit_blockage", seed=42)
    assert len(output.normalized_events) >= 1
    assert output.privacy_report.raw_media_persisted is False
    assert len(output.audit_records) >= 3


@pytest.mark.integration
def test_pipeline_produces_recommendations_for_high_risk_scenario() -> None:
    output = run_pipeline("exit_blockage", seed=42)
    assert len(output.recommendations) >= 1
    assert output.recommendations[0].rationale


@pytest.mark.integration
def test_pipeline_graph_updates_recorded() -> None:
    output = run_pipeline("exit_blockage", seed=42)
    assert len(output.graph_updates) >= 1


@pytest.mark.integration
def test_cli_run_pipeline_json() -> None:
    result = runner.invoke(
        app,
        ["run-pipeline", "--scenario", "exit_blockage", "--seed", "42", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "normalized_events" in payload
    assert "privacy_report" in payload


@pytest.mark.integration
def test_cli_experiment_full_pipeline_json() -> None:
    result = runner.invoke(
        app,
        [
            "experiment",
            "protocol",
            "--scenario",
            "exit_blockage",
            "--protocol",
            "dualexis_full_pipeline",
            "--seed",
            "42",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["protocol_id"] == "dualexis_full_pipeline"
    assert "metrics" in payload
