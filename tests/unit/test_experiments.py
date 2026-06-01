"""Tests for the DUALEXIS experimental battery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dualexis.cli import app
from dualexis.experiments import (
    BATTERY_DISCLAIMER,
    generate_latex_table,
    generate_markdown_report,
    load_experiment_config,
    run_all_batteries,
    run_battery,
)

runner = CliRunner()
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


@pytest.mark.unit
def test_load_experiment_config() -> None:
    config = load_experiment_config(CONFIG_DIR / "exit_blockage.yaml")
    assert config.experiment_id == "exit_blockage"
    assert config.scenario == "exit_blockage"
    assert config.seed == 42


@pytest.mark.unit
def test_battery_run_is_deterministic_with_seed() -> None:
    config = load_experiment_config(CONFIG_DIR / "exit_blockage.yaml")
    first = run_battery(config)
    second = run_battery(config)
    assert first.pipeline_event_count == second.pipeline_event_count
    assert first.deterministic_reproducibility_score == 1.0
    assert first.experiment_metrics.privacy_violation_count == (
        second.experiment_metrics.privacy_violation_count
    )


@pytest.mark.unit
def test_battery_includes_disclaimer() -> None:
    config = load_experiment_config(CONFIG_DIR / "normal_flow.yaml")
    result = run_battery(config)
    assert BATTERY_DISCLAIMER in result.disclaimer


@pytest.mark.unit
def test_markdown_report_contains_measured_values_only(tmp_path: Path) -> None:
    config = load_experiment_config(CONFIG_DIR / "exit_blockage.yaml")
    result = run_battery(config)
    report = generate_markdown_report((result,), output_path=tmp_path / "report.md")
    assert "Measured runs" in report
    assert "exit_blockage" in report
    assert "conclusion" not in report.lower() or "no empirical conclusions" in report.lower()
    assert (tmp_path / "report.md").is_file()


@pytest.mark.unit
def test_latex_table_placeholder(tmp_path: Path) -> None:
    config = load_experiment_config(CONFIG_DIR / "exit_blockage.yaml")
    result = run_battery(config)
    latex = generate_latex_table((result,), output_path=tmp_path / "results.tex")
    assert "\\begin{table}" in latex
    assert "no empirical conclusions" in latex.lower()
    assert (tmp_path / "results.tex").is_file()


@pytest.mark.unit
def test_run_all_writes_json(tmp_path: Path) -> None:
    results = run_all_batteries(tmp_path, config_dir=CONFIG_DIR)
    assert len(results) == 4
    assert (tmp_path / "battery_summary.json").is_file()
    assert (tmp_path / "exit_blockage.json").is_file()


@pytest.mark.unit
def test_cli_experiment_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = CONFIG_DIR / "exit_blockage.yaml"
    result = runner.invoke(
        app,
        ["experiment", "run", "--config", str(config_path), "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["experiment_id"] == "exit_blockage"
    assert payload["privacy_validation_passed"] is True
