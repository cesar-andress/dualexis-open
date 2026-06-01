"""Smoke tests for JSS artifact evaluation outputs."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _table_path(name: str) -> Path:
    reference = ROOT / "results_reference/tables" / name
    if reference.is_file():
        return reference
    return ROOT / "paper/tables" / name


@pytest.mark.unit
def test_harness_honesty_table_present() -> None:
    path = _table_path("harness_honesty.tex")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "tab:harness-honesty" in text


@pytest.mark.unit
def test_privacy_fuzz_table_present() -> None:
    path = _table_path("privacy_fuzz_results.tex")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "tab:privacy-fuzz" in text


@pytest.mark.unit
def test_leakage_audit_table_present() -> None:
    path = _table_path("leakage_audit.tex")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "tab:leakage-audit" in text


@pytest.mark.unit
def test_privacy_fuzz_csv_present() -> None:
    path = ROOT / "results/privacy_fuzz/results.csv"
    assert path.is_file()


@pytest.mark.unit
def test_governance_formal_metrics_present() -> None:
    metrics = ROOT / "results/governance/formal/formal_governance_metrics.csv"
    report = ROOT / "results/governance/formal/governance_audit_report.json"
    assert metrics.is_file()
    assert report.is_file()


@pytest.mark.unit
def test_governance_trace_count_bounded() -> None:
    traces_dir = ROOT / "results/governance/formal/traces"
    assert traces_dir.is_dir()
    count = len(list(traces_dir.glob("*.json")))
    assert 1 <= count <= 100
