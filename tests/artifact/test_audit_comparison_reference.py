"""Verify pinned audit-comparison reference artefacts are deterministic."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dualexis.experiments.audit_comparison_battery import run_audit_comparison_battery

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "results_reference" / "audit_comparison"
TOLERANCE = 1e-4


def _load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_audit_comparison_reference_files_exist() -> None:
    required = (
        "audit_comparison_summary.json",
        "audit_comparison_results.csv",
        "audit_task_results.csv",
        "audit_comparison.tex",
    )
    for name in required:
        assert (REFERENCE / name).is_file(), f"missing pinned artefact: {name}"


@pytest.mark.unit
def test_audit_comparison_tex_label() -> None:
    tex = (REFERENCE / "audit_comparison.tex").read_text(encoding="utf-8")
    assert r"\label{tab:audit-comparison}" in tex
    assert "L_S=0.575" in tex


@pytest.mark.unit
def test_audit_comparison_summary_structure() -> None:
    summary = _load_summary(REFERENCE / "audit_comparison_summary.json")
    assert summary["run_count"] == 180
    assert summary["leakage_score"] == pytest.approx(0.575, abs=1e-6)
    assert set(summary["format_metrics"]) == {"tsgg", "flat_json", "prov"}
    for metrics in summary["format_metrics"].values():
        for key in (
            "query_success_rate",
            "mean_completeness",
            "mean_information_loss",
            "mean_query_hops",
            "violation_f1",
        ):
            assert key in metrics


@pytest.mark.unit
def test_audit_comparison_battery_matches_pinned_summary(tmp_path: Path) -> None:
    """Full 6×30 battery must reproduce pinned aggregate metrics."""
    pin = _load_summary(REFERENCE / "audit_comparison_summary.json")
    report = run_audit_comparison_battery(
        output_dir=tmp_path,
        scenarios=tuple(pin["scenarios"]),
        seeds=tuple(pin["seeds"]),
        leakage_fast=True,
    )
    assert report.leakage_score == pytest.approx(pin["leakage_score"], abs=1e-6)
    for export_format, pin_metrics in pin["format_metrics"].items():
        live = report.format_metrics[export_format]
        assert live.query_success_rate == pytest.approx(
            pin_metrics["query_success_rate"], abs=TOLERANCE
        )
        assert live.mean_completeness == pytest.approx(
            pin_metrics["mean_completeness"], abs=TOLERANCE
        )
        assert live.mean_information_loss == pytest.approx(
            pin_metrics["mean_information_loss"], abs=TOLERANCE
        )
        assert live.mean_query_hops == pytest.approx(pin_metrics["mean_query_hops"], abs=TOLERANCE)
        assert live.violation_f1 == pytest.approx(pin_metrics["violation_f1"], abs=TOLERANCE)


@pytest.mark.unit
def test_audit_comparison_tex_values_match_summary() -> None:
    summary = _load_summary(REFERENCE / "audit_comparison_summary.json")
    tex = (REFERENCE / "audit_comparison.tex").read_text(encoding="utf-8")
    pattern = re.compile(
        r"^\s+(TSGG|Flat JSON|PROV-JSON)\s+&\s+([0-9.]+)\s+&\s+([0-9.]+)\s+&\s+([0-9.]+)\s+&\s+([0-9.]+)\s+&\s+([0-9.]+)\s*\\\\",
        re.MULTILINE,
    )
    label_to_key = {
        "TSGG": "tsgg",
        "Flat JSON": "flat_json",
        "PROV-JSON": "prov",
    }
    for match in pattern.finditer(tex):
        key = label_to_key[match.group(1)]
        metrics = summary["format_metrics"][key]
        assert float(match.group(2)) == pytest.approx(metrics["query_success_rate"], abs=0.001)
        assert float(match.group(3)) == pytest.approx(metrics["mean_completeness"], abs=0.001)
        assert float(match.group(4)) == pytest.approx(metrics["mean_information_loss"], abs=0.001)
        assert float(match.group(5)) == pytest.approx(metrics["mean_query_hops"], abs=0.01)
        assert float(match.group(6)) == pytest.approx(metrics["violation_f1"], abs=0.001)
