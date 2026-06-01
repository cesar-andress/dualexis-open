"""Tests for the DUALEXIS measurement module and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dualexis.cli import app
from dualexis.measurement.export import (
    RESULTS_SUBDIRS,
    ensure_results_layout,
    write_combined_json,
    write_measurement_json,
)
from dualexis.measurement.models import MeasurementKind
from dualexis.measurement.service import measure_all, measure_scenario

runner = CliRunner()


PRIVACY_FIELDS = (
    "privacy_violation_count",
    "raw_media_retention_score",
    "personal_data_exposure_score",
    "human_review_compliance_rate",
)

LATENCY_FIELDS = (
    "end_to_end_latency_ms",
    "event_generation_latency_ms",
    "fusion_latency_ms",
    "graph_update_latency_ms",
    "reasoning_latency_ms",
    "recommendation_latency_ms",
)


@pytest.mark.unit
def test_measurement_output_is_deterministic_with_fixed_seed() -> None:
    first = measure_scenario("exit_blockage", seed=42)
    second = measure_scenario("exit_blockage", seed=42)

    assert first.metrics.deterministic_reproducibility_score == 1.0
    assert second.metrics.deterministic_reproducibility_score == 1.0
    assert first.metrics.number_of_events == second.metrics.number_of_events
    assert first.metrics.number_of_recommendations == second.metrics.number_of_recommendations
    assert first.metrics.privacy_violation_count == second.metrics.privacy_violation_count
    assert first.metrics.raw_media_retention_score == second.metrics.raw_media_retention_score


@pytest.mark.unit
def test_json_export_works(tmp_path: Path) -> None:
    report = measure_scenario("exit_blockage", seed=42)
    target = tmp_path / "measurement.json"
    written = write_measurement_json(report, target)

    assert written.is_file()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["kind"] == MeasurementKind.SCENARIO.value
    assert payload["scenario"] == "exit_blockage"
    assert payload["seed"] == 42
    assert payload["metrics"]["number_of_events"] >= 1


@pytest.mark.unit
def test_latency_metrics_are_non_negative() -> None:
    report = measure_scenario("exit_blockage", seed=42)
    metrics = report.metrics.model_dump()
    for field in LATENCY_FIELDS:
        assert metrics[field] >= 0.0, field


@pytest.mark.unit
def test_privacy_metrics_are_always_present() -> None:
    report = measure_scenario("exit_blockage", seed=42)
    metrics = report.metrics.model_dump()
    for field in PRIVACY_FIELDS:
        assert field in metrics
        assert metrics[field] is not None


@pytest.mark.unit
def test_results_directory_is_created_safely(tmp_path: Path) -> None:
    root = ensure_results_layout(tmp_path / "results")
    assert root.is_dir()
    for name in RESULTS_SUBDIRS:
        assert (root / name).is_dir()

    combined = measure_all("exit_blockage", seed=42, runs=2)
    out_file = tmp_path / "results" / "measurements" / "bundle.json"
    write_combined_json(combined, out_file)
    assert out_file.is_file()


@pytest.mark.unit
def test_cli_measure_scenario_json() -> None:
    result = runner.invoke(
        app,
        ["measure", "scenario", "--scenario", "exit_blockage", "--seed", "42", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["metrics"]["deterministic_reproducibility_score"] == 1.0


@pytest.mark.unit
def test_cli_measure_all_writes_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    output = "results/measurements.json"
    result = runner.invoke(
        app,
        [
            "measure",
            "all",
            "--scenario",
            "exit_blockage",
            "--runs",
            "2",
            "--output",
            output,
        ],
    )
    assert result.exit_code == 0
    assert Path(output).is_file()
