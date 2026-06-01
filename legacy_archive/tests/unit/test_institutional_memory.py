"""Unit tests for Institutional Memory Graphs."""

from __future__ import annotations

from pathlib import Path

from dualexis.institutional_memory.export import (
    build_institutional_memory_report,
    export_institutional_memory,
)
from dualexis.institutional_memory.graph import InstitutionalMemoryGraphBuilder
from dualexis.institutional_memory.miner import GovernancePatternMiner
from dualexis.institutional_memory.near_miss import NearMissDetector
from dualexis.tsgg.pipeline import run_tsgg_record


def test_build_img_from_tsgg_records() -> None:
    records = [run_tsgg_record("exit_blockage", seed=seed) for seed in (1, 2, 3)]
    report = build_institutional_memory_report(records, min_support=1)
    assert report.graph.trace_count >= 0
    assert 0.0 <= report.metrics.memory_coverage <= 1.0
    assert 0.0 <= report.metrics.governance_learning_index <= 1.0
    assert report.graph.dot.startswith("digraph")


def test_miner_and_near_miss() -> None:
    records = [run_tsgg_record("crowd_acceleration", seed=1)]
    traces = list(records[0].governance_traces)
    if not traces:
        return
    patterns = GovernancePatternMiner(min_support=1).mine(traces)
    near = NearMissDetector().detect(traces)
    assert isinstance(patterns, list)
    assert isinstance(near, list)


def test_export_institutional_memory(tmp_path: Path) -> None:
    records = [run_tsgg_record("exit_blockage", seed=1)]
    report = build_institutional_memory_report(records, min_support=1)
    paths = export_institutional_memory(
        report,
        tmp_path / "img",
        paper_sections=tmp_path / "sections",
    )
    assert Path(paths["report_json"]).is_file()
    assert Path(paths["section_tex"]).is_file()
    assert "Institutional Memory" in Path(paths["section_tex"]).read_text(encoding="utf-8")
