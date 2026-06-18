"""Verify pinned decoupled benchmark reference artefacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dualexis.experiments.benchmark_manifest import load_benchmark_manifest
from dualexis.experiments.decoupled_benchmark import run_decoupled_benchmark

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "results_reference" / "benchmark_decoupled"
TOLERANCE = 1e-4


@pytest.mark.unit
def test_decoupled_benchmark_reference_files_exist() -> None:
    for name in (
        "procedural_agreement_summary.json",
        "procedural_agreement_results.csv",
        "procedural_agreement.tex",
    ):
        assert (REFERENCE / name).is_file(), f"missing pinned artefact: {name}"


@pytest.mark.unit
def test_decoupled_benchmark_summary_within_manifest_band() -> None:
    manifest = load_benchmark_manifest()
    summary = json.loads((REFERENCE / "procedural_agreement_summary.json").read_text())
    low, high = manifest.target_par_band
    assert low <= summary["aggregate_par"] <= high


@pytest.mark.unit
def test_decoupled_benchmark_battery_matches_pinned_summary(tmp_path: Path) -> None:
    pin = json.loads((REFERENCE / "procedural_agreement_summary.json").read_text())
    report = run_decoupled_benchmark(
        output_dir=tmp_path,
        scenarios=tuple(pin["scenarios"]),
        seeds=tuple(pin["seeds"]),
        leakage_fast=True,
    )
    assert report.aggregate.par == pytest.approx(pin["aggregate_par"], abs=TOLERANCE)
    assert report.aggregate.fpr == pytest.approx(pin["aggregate_fpr"], abs=TOLERANCE)
    assert report.aggregate.fnr == pytest.approx(pin["aggregate_fnr"], abs=TOLERANCE)
