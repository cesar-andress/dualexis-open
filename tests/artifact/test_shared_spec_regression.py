"""Regression tests for shared-spec supplementary table (NOT primary benchmark)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "results_reference" / "regression" / "shared_spec"


def parse_shared_spec_labels(tex: str) -> dict[str, str]:
    pattern = re.compile(
        r"^\s+([a-z]+(?:\\_[a-z]+)*)\s+&\s+(Pass|Partial|Fail)\s+\\\\\s*$",
        re.MULTILINE,
    )
    return {
        match.group(1).replace(r"\_", "_"): match.group(2)
        for match in pattern.finditer(tex)
    }


@pytest.mark.unit
def test_shared_spec_regression_files_exist() -> None:
    assert (REFERENCE / "shared_spec_regression.json").is_file()
    assert (REFERENCE / "shared_spec_regression.tex").is_file()


@pytest.mark.unit
def test_shared_spec_regression_expected_pass_labels() -> None:
    """Shared-spec mode retains 6/6 Pass as implementation regression only."""
    tex = (REFERENCE / "shared_spec_regression.tex").read_text(encoding="utf-8")
    parsed = parse_shared_spec_labels(tex)
    assert parsed == {
        "normal_flow": "Pass",
        "exit_blockage": "Pass",
        "multimodal_conflict": "Pass",
        "evacuation_recommendation": "Pass",
        "crowd_acceleration": "Pass",
        "audio_stress_signal": "Pass",
    }


@pytest.mark.unit
def test_shared_spec_regression_json_mode_label() -> None:
    summary = json.loads((REFERENCE / "shared_spec_regression.json").read_text())
    assert summary["mode"] == "shared_spec_regression"
    assert "NOT primary" in summary["description"] or "regression" in summary["description"]
