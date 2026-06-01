"""Tests for E2 leakage audit framework."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.leakage_audit.audit import run_leakage_audit
from dualexis.leakage_audit.monte_carlo import run_monte_carlo_scenario
from dualexis.leakage_audit.scoring import INDEPENDENCE_DISCLOSURE, compute_leakage_score
from dualexis.leakage_audit.spec_extraction import (
    extract_all_specs,
    independent_labeler_imports_event_generator,
)


@pytest.mark.unit
def test_procedural_independence_no_generator_import() -> None:
    assert independent_labeler_imports_event_generator() is False


@pytest.mark.unit
def test_extract_specs_non_empty() -> None:
    world, events, rules = extract_all_specs()
    assert world.thresholds
    assert events.thresholds
    assert rules.thresholds


@pytest.mark.unit
def test_leakage_score_bounded() -> None:
    world, events, rules = extract_all_specs()
    from dualexis.leakage_audit.overlap import compute_overlap_report

    overlap = compute_overlap_report(world, events, rules)
    score = compute_leakage_score(overlap)
    assert 0.0 <= score <= 1.0


@pytest.mark.unit
def test_monte_carlo_smoke() -> None:
    result = run_monte_carlo_scenario("exit_blockage", seed=1, iterations=5)
    assert 0.0 <= result.ground_truth_stability <= 1.0
    assert result.event_stability == 1.0


@pytest.mark.unit
def test_run_leakage_audit_exports(tmp_path: Path) -> None:
    report = run_leakage_audit(
        output_dir=tmp_path / "audit",
        paper_tables=tmp_path / "tables",
        paper_sections=tmp_path / "sections",
        scenarios=("exit_blockage", "normal_flow"),
        monte_carlo_iterations=10,
        fast=True,
    )
    assert INDEPENDENCE_DISCLOSURE in report.independence_disclosure
    assert (tmp_path / "audit" / "leakage_audit_report.json").is_file()
    assert (tmp_path / "tables" / "leakage_audit.tex").is_file()
    assert (tmp_path / "sections" / "leakage_analysis.tex").is_file()
