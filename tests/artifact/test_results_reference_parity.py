"""Verify pinned results_reference artefacts match fresh results/ outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dualexis.evaluation.harness_honesty_export import (
    HarnessHonestyPaths,
    load_harness_honesty_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
REFERENCE = ROOT / "results_reference"
TOLERANCE = 0.01

GOVERNANCE_METRIC_KEYS = (
    "governance_compliance_score",
    "institutional_reliance_index",
    "human_override_resilience",
    "decision_traceability",
)


def _require_live_results() -> None:
    if not RESULTS.is_dir():
        pytest.skip("results/ not present; run artifact/commands.sh first")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_pinned_governance_metrics_match_live_results() -> None:
    _require_live_results()
    live = RESULTS / "governance/formal/governance_audit_report.json"
    pin = REFERENCE / "governance/formal/governance_audit_report.json"
    assert live.is_file(), "missing live governance audit report"
    assert pin.is_file(), "missing pinned governance audit report"

    live_metrics = _load_json(live)["metrics"]
    pin_metrics = _load_json(pin)["metrics"]
    for key in GOVERNANCE_METRIC_KEYS:
        assert live_metrics[key] == pytest.approx(pin_metrics[key], abs=1e-6), key


@pytest.mark.unit
def test_pinned_leakage_report_matches_live_results() -> None:
    _require_live_results()
    live = RESULTS / "leakage_audit/leakage_audit_report.json"
    pin = REFERENCE / "leakage_audit/leakage_audit_report.json"
    assert live.is_file() and pin.is_file()

    live_report = _load_json(live)
    pin_report = _load_json(pin)
    assert live_report["leakage_score"] == pytest.approx(pin_report["leakage_score"], abs=1e-6)
    for layer in ("procedural_independence", "distributional_independence"):
        assert live_report["independence"][layer] == pytest.approx(
            pin_report["independence"][layer], abs=1e-4
        )


@pytest.mark.unit
def test_pinned_trust_report_matches_live_results() -> None:
    _require_live_results()
    live = RESULTS / "tsgg/trust/trust_propagation_report.json"
    pin = REFERENCE / "tsgg/trust/trust_propagation_report.json"
    assert live.is_file() and pin.is_file()

    live_trust = _load_json(live)["metrics"]["mean_path_trust"]
    pin_trust = _load_json(pin)["metrics"]["mean_path_trust"]
    assert live_trust == pytest.approx(pin_trust, abs=1e-4)


@pytest.mark.unit
def test_pinned_privacy_csv_matches_live_results() -> None:
    _require_live_results()
    live = RESULTS / "privacy_fuzz/results.csv"
    pin = REFERENCE / "privacy_fuzz/results.csv"
    assert live.is_file() and pin.is_file()
    assert live.read_bytes() == pin.read_bytes()


@pytest.mark.unit
def test_pinned_baseline_csv_matches_live_results() -> None:
    _require_live_results()
    live = RESULTS / "baseline_comparison/results.csv"
    pin = REFERENCE / "baseline_comparison/results.csv"
    assert live.is_file() and pin.is_file()
    assert live.read_bytes() == pin.read_bytes()


@pytest.mark.unit
def test_harness_honesty_tex_matches_live_source_artefacts() -> None:
    _require_live_results()
    paths = HarnessHonestyPaths(
        leakage_report=RESULTS / "leakage_audit/leakage_audit_report.json",
        privacy_fuzz_csv=RESULTS / "privacy_fuzz/results.csv",
        governance_report=RESULTS / "governance/formal/governance_audit_report.json",
        trust_report=RESULTS / "tsgg/trust/trust_propagation_report.json",
    )
    for path in (
        paths.leakage_report,
        paths.privacy_fuzz_csv,
        paths.governance_report,
        paths.trust_report,
    ):
        assert path.is_file(), f"missing live artefact: {path}"

    metrics = load_harness_honesty_metrics(paths)
    tex = (REFERENCE / "tables/harness_honesty.tex").read_text(encoding="utf-8")

    import re

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
    parsed = dict(
        zip(
            keys,
            [float(m.group(1)) for m in pattern.finditer(tex)],
            strict=True,
        )
    )

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
def test_shared_spec_regression_tex_all_pass() -> None:
    """Shared-spec regression table is supplementary; not derived from B5 baseline CSV."""
    tex = (
        REFERENCE / "regression/shared_spec/shared_spec_regression.tex"
    ).read_text(encoding="utf-8")

    import re

    pattern = re.compile(
        r"^\s+([a-z]+(?:\\_[a-z]+)*)\s+&\s+(Pass|Partial|Fail)\s+\\\\\s*$",
        re.MULTILINE,
    )
    parsed = {
        match.group(1).replace(r"\_", "_"): match.group(2)
        for match in pattern.finditer(tex)
    }
    assert parsed
    assert all(label == "Pass" for label in parsed.values())
