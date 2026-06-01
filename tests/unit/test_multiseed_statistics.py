"""Tests for post-hoc multiseed statistics."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.experiments.multiseed_statistics import (
    bootstrap_ci,
    compute_paired_deltas,
    compute_stability_table,
    export_analysis_bundle,
    load_baseline_csv,
    rank_stability_across_seeds,
    student_t_ci,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = REPO_ROOT / "results/baseline_comparison/results.csv"


@pytest.mark.unit
def test_student_t_degenerate_interval() -> None:
    interval = student_t_ci([0.5, 0.5, 0.5])
    assert interval.mean == 0.5
    assert interval.ci_low == interval.ci_high == 0.5


@pytest.mark.unit
def test_bootstrap_interval_on_varying_values() -> None:
    values = [0.375] * 22 + [0.4118] * 8
    interval = bootstrap_ci(values, n_resamples=1000, seed=1)
    assert interval.ci_low <= interval.mean <= interval.ci_high


@pytest.mark.skipif(not CSV_PATH.is_file(), reason="baseline CSV not generated")
@pytest.mark.unit
def test_export_analysis_bundle(tmp_path: Path) -> None:
    out = export_analysis_bundle(CSV_PATH, tmp_path, bootstrap_resamples=500)
    assert (out / "stability.csv").is_file()
    assert (out / "multiseed_statistics.tex").is_file()
    assert (out / "summary.json").is_file()


@pytest.mark.skipif(not CSV_PATH.is_file(), reason="baseline CSV not generated")
@pytest.mark.unit
def test_rank_stability_perfect_for_normal_flow() -> None:
    rows = load_baseline_csv(CSV_PATH)
    ranks = rank_stability_across_seeds(rows)
    normal = next(r for r in ranks if r["scenario"] == "normal_flow")
    assert normal["rank_agreement_fraction"] == 1.0


@pytest.mark.skipif(not CSV_PATH.is_file(), reason="baseline CSV not generated")
@pytest.mark.unit
def test_paired_b5_b1_constant_delta_exit_blockage() -> None:
    rows = load_baseline_csv(CSV_PATH)
    paired = compute_paired_deltas(rows, baseline_a="B5", baseline_b="B1")
    exit_row = next(p for p in paired if p.scenario == "exit_blockage")
    assert exit_row.mean_delta == 0.0
    assert exit_row.win_rate_b == 0.0
