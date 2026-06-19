"""Verify pinned coupling-controlled PAR reference artefacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "results_reference" / "coupling_controlled_par"


@pytest.mark.unit
def test_coupling_controlled_par_reference_files_exist() -> None:
    for name in (
        "coupling_controlled_par.csv",
        "coupling_controlled_par.json",
        "coupling_controlled_par.tex",
        "coupling_controlled_par_by_run.csv",
    ):
        assert (REFERENCE / name).is_file(), f"missing pinned artefact: {name}"


@pytest.mark.unit
def test_coupling_controlled_par_summary_has_lambda_endpoints() -> None:
    payload = json.loads((REFERENCE / "coupling_controlled_par.json").read_text())
    lambdas = {row["lambda"] for row in payload["aggregate"]}
    assert 0.0 in lambdas
    assert 1.0 in lambdas
    assert payload["chance_permutations"] >= 1000


@pytest.mark.unit
def test_coupling_controlled_par_lambda_zero_near_decoupled_benchmark() -> None:
    payload = json.loads((REFERENCE / "coupling_controlled_par.json").read_text())
    zone_zero = next(
        row for row in payload["aggregate"] if row["channel"] == "zone_permutation" and row["lambda"] == 0.0
    )
    assert zone_zero["par"] == pytest.approx(0.925, abs=0.02)
