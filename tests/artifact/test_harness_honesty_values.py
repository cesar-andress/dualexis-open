"""Regression tests for regenerated harness honesty Table 7 values."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dualexis.evaluation.harness_honesty_export import (
    AUTO_GENERATED_BANNER,
    HarnessHonestyPaths,
    load_harness_honesty_metrics,
    load_privacy_fuzz_pass_rate,
)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "results_reference"
TOLERANCE = 0.01


def _resolve_paths() -> HarnessHonestyPaths:
    """Prefer live results/ after commands.sh; fall back to pinned reference copies."""
    results = ROOT / "results"
    ref_leakage = REFERENCE / "leakage_audit/leakage_audit_report.json"
    ref_privacy = REFERENCE / "privacy_fuzz/results.csv"
    ref_governance = REFERENCE / "governance/formal/governance_audit_report.json"
    ref_trust = REFERENCE / "tsgg/trust/trust_propagation_report.json"

    return HarnessHonestyPaths(
        leakage_report=(
            results / "leakage_audit/leakage_audit_report.json"
            if (results / "leakage_audit/leakage_audit_report.json").is_file()
            else ref_leakage
        ),
        privacy_fuzz_csv=(
            results / "privacy_fuzz/results.csv"
            if (results / "privacy_fuzz/results.csv").is_file()
            else ref_privacy
        ),
        governance_report=(
            results / "governance/formal/governance_audit_report.json"
            if (results / "governance/formal/governance_audit_report.json").is_file()
            else ref_governance
        ),
        trust_report=(
            results / "tsgg/trust/trust_propagation_report.json"
            if (results / "tsgg/trust/trust_propagation_report.json").is_file()
            else ref_trust
        ),
    )


def parse_harness_honesty_values(tex: str) -> dict[str, float]:
    pattern = re.compile(r"^\s+.+?&\s*([0-9.]+)\s*\\\\\s*$", re.MULTILINE)
    keys = [
        "leakage_score",
        "procedural_independence",
        "distributional_independence",
        "privacy_fuzz_pass_rate",
        "governance_compliance",
        "decision_traceability",
        "mean_path_trust",
    ]
    values = [float(match.group(1)) for match in pattern.finditer(tex)]
    return dict(zip(keys, values, strict=True))


@pytest.mark.unit
def test_harness_honesty_auto_generated_banner() -> None:
    path = ROOT / "results_reference/tables/harness_honesty.tex"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.startswith(AUTO_GENERATED_BANNER.strip().splitlines()[0])


@pytest.mark.unit
def test_harness_honesty_matches_source_artefacts() -> None:
    paths = _resolve_paths()
    if not paths.trust_report.is_file():
        pytest.skip("trust_propagation_report.json not yet generated; run commands.sh")

    metrics = load_harness_honesty_metrics(paths)
    tex_path = ROOT / "results_reference/tables/harness_honesty.tex"
    parsed = parse_harness_honesty_values(tex_path.read_text(encoding="utf-8"))

    assert parsed["leakage_score"] == pytest.approx(metrics.leakage_score, abs=TOLERANCE)
    assert parsed["procedural_independence"] == pytest.approx(
        metrics.procedural_independence, abs=TOLERANCE
    )
    assert parsed["distributional_independence"] == pytest.approx(
        metrics.distributional_independence, abs=TOLERANCE
    )
    assert parsed["privacy_fuzz_pass_rate"] == pytest.approx(
        metrics.privacy_fuzz_pass_rate, abs=TOLERANCE
    )
    assert parsed["governance_compliance"] == pytest.approx(
        metrics.governance_compliance_score, abs=TOLERANCE
    )
    assert parsed["decision_traceability"] == pytest.approx(
        metrics.decision_traceability, abs=TOLERANCE
    )
    assert parsed["mean_path_trust"] == pytest.approx(metrics.mean_path_trust, abs=TOLERANCE)


@pytest.mark.unit
def test_harness_honesty_footer_gt_stability() -> None:
    paths = _resolve_paths()
    leakage = json.loads(paths.leakage_report.read_text(encoding="utf-8"))
    tex = (ROOT / "results_reference/tables/harness_honesty.tex").read_text(encoding="utf-8")
    gt = leakage["ground_truth_stability_mean"]
    if abs(gt - 0.5) < 0.05:
        assert "GT stability ${\\approx}0.5$" in tex
    else:
        assert f"{gt:.3f}" in tex


@pytest.mark.unit
def test_harness_honesty_privacy_csv_pass_rate() -> None:
    paths = _resolve_paths()
    _, _, rate = load_privacy_fuzz_pass_rate(paths.privacy_fuzz_csv)
    tex = (ROOT / "results_reference/tables/harness_honesty.tex").read_text(encoding="utf-8")
    parsed = parse_harness_honesty_values(tex)
    assert parsed["privacy_fuzz_pass_rate"] == pytest.approx(rate, abs=TOLERANCE)
