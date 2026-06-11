"""Regression tests for regenerated harness honesty Table 8 values."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dualexis.evaluation.harness_b5_alignment import load_harness_b5_alignment
from dualexis.evaluation.harness_b5_labels_export import AUTO_GENERATED_BANNER

ROOT = Path(__file__).resolve().parents[2]


def _resolve_baseline_csv() -> Path:
    live = ROOT / "results/baseline_comparison/results.csv"
    reference = ROOT / "results_reference/baseline_comparison/results.csv"
    if live.is_file():
        return live
    if reference.is_file():
        return reference
    pytest.skip("baseline results.csv not found; run commands.sh")


def parse_harness_b5_labels(tex: str) -> dict[str, str]:
    pattern = re.compile(
        r"^\s+([a-z]+(?:\\_[a-z]+)*)\s+&\s+(Pass|Partial|Fail)\s+\\\\\s*$",
        re.MULTILINE,
    )
    return {
        match.group(1).replace(r"\_", "_"): match.group(2)
        for match in pattern.finditer(tex)
    }


@pytest.mark.unit
def test_harness_b5_auto_generated_banner() -> None:
    path = ROOT / "results_reference/tables/harness_b5_by_scenario.tex"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.startswith(AUTO_GENERATED_BANNER.strip().splitlines()[0])


@pytest.mark.unit
def test_harness_b5_matches_baseline_csv() -> None:
    csv_path = _resolve_baseline_csv()
    alignment = load_harness_b5_alignment(csv_path)
    tex_path = ROOT / "results_reference/tables/harness_b5_by_scenario.tex"
    parsed = parse_harness_b5_labels(tex_path.read_text(encoding="utf-8"))

    assert len(parsed) == len(alignment.rows)
    for row in alignment.rows:
        assert parsed[row.scenario] == row.label


@pytest.mark.unit
def test_harness_b5_expected_reference_labels() -> None:
    """Sanity check against published Pass/Partial/Fail disclosure."""
    tex_path = ROOT / "results_reference/tables/harness_b5_by_scenario.tex"
    parsed = parse_harness_b5_labels(tex_path.read_text(encoding="utf-8"))
    assert parsed == {
        "normal_flow": "Pass",
        "exit_blockage": "Partial",
        "multimodal_conflict": "Fail",
        "evacuation_recommendation": "Fail",
        "crowd_acceleration": "Fail",
        "audio_stress_signal": "Fail",
    }
