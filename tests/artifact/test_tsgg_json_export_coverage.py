"""TSGG JSON export coverage for the six bundled scenarios."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dualexis.tsgg.audit import PAPER_SCENARIOS, run_tsgg_framework

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_paper_scenarios_count_is_six() -> None:
    assert PAPER_SCENARIOS == (
        "normal_flow",
        "exit_blockage",
        "multimodal_conflict",
        "evacuation_recommendation",
        "crowd_acceleration",
        "audio_stress_signal",
    )


@pytest.mark.unit
def test_tsgg_framework_writes_six_scenario_trace_json(tmp_path: Path) -> None:
    """Optional workflow step: experiment tsgg-framework (not in commands.sh)."""
    output = tmp_path / "tsgg"
    report = run_tsgg_framework(
        output_dir=output,
        scenarios=PAPER_SCENARIOS,
        seeds=(1,),
        leakage_fast=True,
    )

    assert report.framework_json.is_file()
    payload = json.loads(report.framework_json.read_text(encoding="utf-8"))
    scenario_ids = {record["scenario_id"] for record in payload["run_records"]}
    assert scenario_ids == set(PAPER_SCENARIOS)

    traces_dir = output / "traces"
    trace_files = sorted(traces_dir.glob("*.json"))
    assert len(trace_files) == len(PAPER_SCENARIOS)

    for scenario in PAPER_SCENARIOS:
        matches = list(traces_dir.glob(f"{scenario}_seed1.json"))
        assert len(matches) == 1
        trace = json.loads(matches[0].read_text(encoding="utf-8"))
        assert trace["scenario_id"] == scenario
        assert trace["stage_counts"]
