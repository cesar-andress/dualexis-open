"""Tests for multi-seed experimental battery execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.experiments import (
    compute_descriptive_stats,
    compute_multiseed_aggregates,
    generate_multiseed_latex_table,
    load_experiment_config,
    run_battery,
    run_multiseed_batteries,
)

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


@pytest.mark.unit
def test_deterministic_same_seed_outputs() -> None:
    config = load_experiment_config(CONFIG_DIR / "exit_blockage.yaml")
    first = run_battery(config, seed=42)
    second = run_battery(config, seed=42)
    assert first.pipeline_event_count == second.pipeline_event_count
    assert first.deterministic_reproducibility_score == 1.0
    assert second.deterministic_reproducibility_score == 1.0
    assert (
        first.experiment_metrics.privacy_violation_count
        == second.experiment_metrics.privacy_violation_count
    )


@pytest.mark.unit
def test_different_seed_outputs_are_collected(tmp_path: Path) -> None:
    config_path = CONFIG_DIR / "exit_blockage.yaml"
    single_config_dir = tmp_path / "configs"
    single_config_dir.mkdir()
    single_config_dir.joinpath("exit_blockage.yaml").write_text(
        config_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = run_multiseed_batteries(
        tmp_path / "out",
        config_dir=single_config_dir,
        seeds=(1, 42),
    )

    assert report.run_count == 2
    assert {run.seed for run in report.runs} == {1, 42}
    assert (tmp_path / "out" / "runs" / "exit_blockage_seed_1.json").is_file()
    assert (tmp_path / "out" / "runs" / "exit_blockage_seed_42.json").is_file()


@pytest.mark.unit
def test_aggregate_metrics_are_computed() -> None:
    config = load_experiment_config(CONFIG_DIR / "exit_blockage.yaml")
    runs = [run_battery(config, seed=seed) for seed in (1, 42)]
    aggregates = compute_multiseed_aggregates(runs)
    assert len(aggregates) == 1

    events = aggregates[0].pipeline_event_count
    assert events.count == 2
    assert events.minimum <= events.mean <= events.maximum
    assert events.std >= 0.0

    stats = compute_descriptive_stats([1.0, 3.0])
    assert stats.mean == 2.0
    assert stats.minimum == 1.0
    assert stats.maximum == 3.0


@pytest.mark.unit
def test_latex_table_is_generated(tmp_path: Path) -> None:
    config_path = CONFIG_DIR / "exit_blockage.yaml"
    single_config_dir = tmp_path / "configs"
    single_config_dir.mkdir()
    single_config_dir.joinpath("exit_blockage.yaml").write_text(
        config_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = run_multiseed_batteries(
        tmp_path / "out",
        config_dir=single_config_dir,
        seeds=(42,),
    )
    latex_path = tmp_path / "out" / "multiseed_results.tex"
    assert latex_path.is_file()
    latex = latex_path.read_text(encoding="utf-8")
    assert "\\begin{table}" in latex
    assert "no significance" in latex.lower() or "No statistical significance" in latex

    regenerated = generate_multiseed_latex_table(report, output_path=tmp_path / "custom.tex")
    assert "multiseed-scaffold" in regenerated
