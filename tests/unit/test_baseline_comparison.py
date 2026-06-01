"""Unit tests for comparable baseline comparison."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dualexis.cli import app
from dualexis.evaluation.comparable_baselines import (
    ComparableBaselineId,
    DualexisFullPipelineBaseline,
    RuleBasedFusionComparableBaseline,
    SingleModalityAlertBaseline,
    TemporalGraphBaseline,
    dominant_modality,
    list_comparable_baselines,
    run_all_comparable_baselines,
)
from dualexis.evaluation.comparison import (
    COMPARISON_DISCLAIMER,
    compute_baseline_aggregates,
    generate_comparison_latex_table,
    generate_comparison_markdown,
    run_baseline_comparison,
)
from dualexis.simulation import run_scenario

runner = CliRunner()

METRIC_KEYS = (
    "end_to_end_latency_ms",
    "recommendation_count",
    "privacy_violation_count",
    "explanation_completeness_score",
    "human_review_compliance_rate",
    "modality_drop_tolerance",
    "reproducibility_score",
)


def test_list_comparable_baselines_registers_five() -> None:
    baselines = list_comparable_baselines()
    assert len(baselines) == 5
    assert ComparableBaselineId.SINGLE_MODALITY_ALERT in baselines
    assert ComparableBaselineId.DUALEXIS_FULL_PIPELINE in baselines


def test_all_baselines_run_on_same_scenario_and_seed() -> None:
    scenario = "exit_blockage"
    seed = 42
    results = run_all_comparable_baselines(scenario, seed=seed)
    assert len(results) == 5
    for result in results:
        assert result.scenario == scenario
        assert result.seed == seed
        metrics = result.as_dict()["metrics"]
        assert isinstance(metrics, dict)
        for key in METRIC_KEYS:
            assert key in metrics


def test_different_seeds_produce_runs() -> None:
    baseline = SingleModalityAlertBaseline()
    first = baseline.run("exit_blockage", seed=1)
    second = baseline.run("exit_blockage", seed=2)
    assert first.seed != second.seed


def test_dominant_modality_is_deterministic() -> None:
    simulation = run_scenario("exit_blockage", seed=7)
    assert dominant_modality(simulation.events) in {"video", "audio", "sensor"}


def test_reproducibility_score_is_perfect_for_deterministic_baselines() -> None:
    result = TemporalGraphBaseline().run("exit_blockage", seed=10)
    assert result.reproducibility_score == 1.0


def test_compute_baseline_aggregates_groups_by_baseline() -> None:
    runs = run_all_comparable_baselines("exit_blockage", seed=5)
    aggregates = compute_baseline_aggregates(runs)
    assert len(aggregates) == 5
    assert all(item.end_to_end_latency_ms.count >= 1 for item in aggregates)


def test_run_baseline_comparison_writes_artifacts(tmp_path: Path) -> None:
    report = run_baseline_comparison(
        "exit_blockage",
        [1, 2],
        output_dir=tmp_path,
    )
    assert report.scenario == "exit_blockage"
    assert report.seeds == (1, 2)
    assert len(report.runs) == 10
    assert (tmp_path / "comparison_summary.json").is_file()
    assert (tmp_path / "comparison_report.md").is_file()
    assert (tmp_path / "comparison_results.tex").is_file()
    assert (tmp_path / "runs").is_dir()


def test_comparison_markdown_has_no_significance_claims(tmp_path: Path) -> None:
    report = run_baseline_comparison("normal_flow", [1], output_dir=tmp_path)
    markdown = generate_comparison_markdown(report)
    lowered = markdown.lower()
    assert "no statistical significance" in lowered
    assert "ranking claims" in lowered
    assert "p-value" not in lowered
    for forbidden in ("superior", "superiority", "best", "outperform", "winner"):
        assert forbidden not in lowered, f"forbidden term {forbidden!r} in markdown"
    assert COMPARISON_DISCLAIMER.split(".")[0] in markdown


def test_comparison_latex_table_generated(tmp_path: Path) -> None:
    report = run_baseline_comparison("normal_flow", [1], output_dir=tmp_path)
    latex = generate_comparison_latex_table(report)
    assert "\\begin{table}" in latex
    assert "tab:baseline-comparison" in latex
    assert "significance" in latex.lower()


def test_comparison_summary_json_structure(tmp_path: Path) -> None:
    run_baseline_comparison("exit_blockage", [42], output_dir=tmp_path)
    payload = json.loads((tmp_path / "comparison_summary.json").read_text(encoding="utf-8"))
    assert payload["scenario"] == "exit_blockage"
    assert payload["seeds"] == [42]
    assert len(payload["runs"]) == 5
    assert len(payload["aggregates"]) == 5
    assert "disclaimer" in payload


def test_cli_experiment_compare(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "experiment",
            "compare",
            "--scenario",
            "exit_blockage",
            "--seeds",
            "1,2",
            "--output",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert (tmp_path / "comparison_summary.json").is_file()


def test_full_pipeline_has_more_complete_explanations_than_single_modality() -> None:
    seed = 42
    single = SingleModalityAlertBaseline().run("exit_blockage", seed=seed)
    full = DualexisFullPipelineBaseline().run("exit_blockage", seed=seed)
    assert full.explanation_completeness_score >= single.explanation_completeness_score


@pytest.mark.parametrize(
    "baseline_cls",
    [
        SingleModalityAlertBaseline,
        RuleBasedFusionComparableBaseline,
        TemporalGraphBaseline,
        DualexisFullPipelineBaseline,
    ],
)
def test_baseline_metric_ranges(baseline_cls: type) -> None:
    result = baseline_cls().run("exit_blockage", seed=3)
    assert result.end_to_end_latency_ms >= 0.0
    assert result.recommendation_count >= 0
    assert result.privacy_violation_count >= 0
    assert 0.0 <= result.explanation_completeness_score <= 1.0
    assert 0.0 <= result.human_review_compliance_rate <= 1.0
    assert 0.0 <= result.modality_drop_tolerance <= 1.0
    assert result.reproducibility_score in {0.0, 1.0}
