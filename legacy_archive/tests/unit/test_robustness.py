"""Tests for multiseed robustness audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.robustness.audit import audit_scenario_robustness, run_robustness_audit
from dualexis.robustness.export import export_robustness_audit, write_robustness_plot_tex
from dualexis.robustness.stability import (
    compute_robustness_score,
    distribution_from_values,
    jaccard_similarity,
    mean_pairwise_jaccard,
)
from dualexis.robustness.models import StabilityMetricKind
from dualexis.robustness.signatures import collect_signatures
from dualexis.experiments.robustness_battery import run_robustness_battery


@pytest.mark.unit
def test_jaccard_identical() -> None:
    sig = frozenset({"a", "b"})
    assert jaccard_similarity(sig, sig) == 1.0


@pytest.mark.unit
def test_mean_pairwise_jaccard() -> None:
    assert mean_pairwise_jaccard([frozenset({"a"}), frozenset({"a"})]) == 1.0


@pytest.mark.unit
def test_distribution_from_values() -> None:
    dist = distribution_from_values(
        StabilityMetricKind.EVENT,
        [1.0, 0.9, 0.95],
    )
    assert dist.mean > 0.9
    assert dist.std >= 0.0
    assert dist.coefficient_of_variation >= 0.0


@pytest.mark.unit
def test_robustness_score_bounded() -> None:
    dists = [
        distribution_from_values(StabilityMetricKind.EVENT, [0.9, 0.95]),
        distribution_from_values(StabilityMetricKind.STATE, [0.8, 0.85]),
    ]
    score = compute_robustness_score(dists)
    assert 0.0 <= score <= 1.0


@pytest.mark.unit
def test_collect_signatures_exit_blockage() -> None:
    sigs = collect_signatures("exit_blockage", seed=1)
    assert isinstance(sigs.event, frozenset)
    assert isinstance(sigs.state, frozenset)


@pytest.mark.unit
def test_audit_scenario_robustness() -> None:
    result = audit_scenario_robustness("exit_blockage", seeds=(1, 2))
    assert 0.0 <= result.event_stability <= 1.0
    assert len(result.distributions) == 4


@pytest.mark.unit
def test_robustness_battery_fast(tmp_path: Path) -> None:
    report = run_robustness_battery(
        output_dir=tmp_path / "rob",
        paper_figures=tmp_path / "figures",
        paper_sections=tmp_path / "sections",
        seeds=(1, 2),
        scenarios=("exit_blockage",),
    )
    assert (tmp_path / "rob" / "robustness_audit_report.json").is_file()
    assert report.section_tex.is_file()
    assert 0.0 <= report.report.robustness_score <= 1.0


@pytest.mark.unit
def test_write_robustness_plot_tex(tmp_path: Path) -> None:
    series = {
        "event": [(1, 1.0), (2, 0.95)],
        "state": [(1, 1.0), (2, 0.9)],
        "recommendation": [(1, 1.0), (2, 1.0)],
        "explanation": [(1, 0.9), (2, 0.88)],
    }
    tex_path = tmp_path / "robustness_vs_seed.tex"
    write_robustness_plot_tex(series, tex_path)
    assert "addplot" in tex_path.read_text(encoding="utf-8")
