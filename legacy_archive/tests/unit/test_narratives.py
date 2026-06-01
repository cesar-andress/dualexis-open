"""Unit tests for longitudinal safety narratives."""

from __future__ import annotations

from pathlib import Path

from dualexis.narratives.export import build_longitudinal_report, export_longitudinal_narratives
from dualexis.narratives.generator import NarrativeGenerator
from dualexis.narratives.models import NarrativeStageKind
from dualexis.tsgg.pipeline import run_tsgg_record


def test_narrative_generator_exit_blockage() -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    trace = NarrativeGenerator().generate_primary(record)
    assert trace.beats
    assert "08:" in trace.beats[0].clock_label
    stages = {beat.stage for beat in trace.beats}
    assert NarrativeStageKind.STATE_CHANGE in stages or NarrativeStageKind.EVIDENCE in stages
    assert 0.0 <= trace.metrics.narrative_completeness <= 1.0


def test_rendered_timeline_format() -> None:
    record = run_tsgg_record("crowd_acceleration", seed=2)
    trace = NarrativeGenerator().generate_primary(record)
    lines = trace.rendered_text.split("\n")
    assert len(lines) >= 2
    assert lines[0].count(":") == 1


def test_condensed_narrative_arc() -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    trace = NarrativeGenerator().generate_primary(record)
    assert len(trace.beats) <= 8
    stages = [beat.stage for beat in trace.beats]
    assert NarrativeStageKind.EVIDENCE in stages


def test_export_longitudinal_narratives(tmp_path: Path) -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    report = build_longitudinal_report([record])
    paths = export_longitudinal_narratives(
        report,
        tmp_path / "narratives",
        paper_sections=tmp_path / "sections",
    )
    assert Path(paths["report_json"]).is_file()
    assert Path(paths["section_tex"]).is_file()
    assert "Longitudinal" in Path(paths["section_tex"]).read_text(encoding="utf-8")
