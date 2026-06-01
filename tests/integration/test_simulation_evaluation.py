"""Integration tests for simulation-backed experimental evaluation."""

from __future__ import annotations

import json
import re

import pytest
from typer.testing import CliRunner

from dualexis.cli import app
from dualexis.evaluation import (
    SCAFFOLD_DISCLAIMER,
    ExperimentProtocolId,
    format_experiment_summary,
    list_protocols,
    run_experiment,
)
from dualexis.paper.check import repo_root

runner = CliRunner()

PAPER_RESULT_SECTIONS = (
    "sections/evaluation_plan.tex",
    "sections/metrics.tex",
    "sections/methodology.tex",
    "sections/results_scaffold.tex",
    "sections/baselines.tex",
    "sections/contributions.tex",
    "sections/threats_to_validity.tex",
    "tables/results.tex",
)

FABRICATED_CONCLUSION_PATTERNS = (
    re.compile(r"significantly\s+outperforms?", re.IGNORECASE),
    re.compile(r"p\s*<\s*0\.05", re.IGNORECASE),
    re.compile(r"DUALEXIS achieves \d+\s*%", re.IGNORECASE),
    re.compile(r"we demonstrate superiority", re.IGNORECASE),
)


@pytest.mark.integration
def test_all_protocols_registered() -> None:
    assert {protocol.value for protocol in list_protocols()} == {
        protocol.value for protocol in ExperimentProtocolId
    }


@pytest.mark.integration
@pytest.mark.parametrize("protocol", [protocol.value for protocol in ExperimentProtocolId])
def test_experiments_are_reproducible_with_seed(protocol: str) -> None:
    first = run_experiment("exit_blockage", protocol, seed=42)
    second = run_experiment("exit_blockage", protocol, seed=42)
    assert first.metrics.model_dump() == second.metrics.model_dump()


@pytest.mark.integration
def test_experiment_metrics_are_computed() -> None:
    report = run_experiment("exit_blockage", "dualexis_full_pipeline", seed=42)
    metrics = report.metrics
    assert metrics.end_to_end_latency_ms > 0.0
    assert 0.0 <= metrics.event_detection_accuracy <= 1.0
    assert 0.0 <= metrics.false_positive_rate <= 1.0
    assert 0.0 <= metrics.false_negative_rate <= 1.0
    assert metrics.time_to_recommendation_ms > 0.0
    assert 0.0 <= metrics.explanation_completeness_score <= 1.0
    assert 0.0 <= metrics.human_review_compliance_rate <= 1.0
    assert metrics.graph_update_latency_ms >= 0.0


@pytest.mark.integration
def test_experiment_report_generated_with_scaffold_disclaimer() -> None:
    report = run_experiment("exit_blockage", "rule_based_fusion_baseline", seed=7)
    summary = format_experiment_summary(report)
    assert "scenario=exit_blockage" in summary
    assert "protocol=rule_based_fusion_baseline" in summary
    assert SCAFFOLD_DISCLAIMER in report.notes


@pytest.mark.integration
def test_cli_experiment_command() -> None:
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
        ],
    )
    assert result.exit_code == 0
    assert "event_detection_accuracy=" in result.stdout
    assert "privacy_violation_count=" in result.stdout


@pytest.mark.integration
def test_cli_experiment_json_output() -> None:
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
    assert payload["metrics"]["privacy_violation_count"] >= 0
    assert payload["metrics"]["raw_data_retention_score"] is not None


@pytest.mark.integration
def test_paper_contains_no_fabricated_conclusions() -> None:
    paper_dir = repo_root() / "paper"
    for relative in PAPER_RESULT_SECTIONS:
        content = (paper_dir / relative).read_text(encoding="utf-8")
        for pattern in FABRICATED_CONCLUSION_PATTERNS:
            assert pattern.search(content) is None, (
                f"Fabricated conclusion pattern {pattern.pattern!r} found in {relative}"
            )
    evaluation_plan = (paper_dir / "sections/evaluation_plan.tex").read_text(encoding="utf-8")
    assert "\\textit{TBD}" in evaluation_plan
    assert "No inferential experimental results are reported" in evaluation_plan
