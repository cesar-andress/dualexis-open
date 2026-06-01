"""Tests for ontology drift detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.ontology_drift.detection import run_ontology_drift_detection
from dualexis.ontology_drift.export import export_ontology_drift_report
from dualexis.ontology_drift.metrics import drift_from_stability, mean_pairwise_jaccard
from dualexis.ontology_drift.snapshots import collect_ontology_snapshot


@pytest.mark.unit
def test_mean_pairwise_jaccard_identical() -> None:
    sig = frozenset({"a", "b"})
    assert mean_pairwise_jaccard([sig, sig]) == 1.0
    assert drift_from_stability(1.0) == 0.0


@pytest.mark.unit
def test_collect_ontology_snapshot() -> None:
    snap = collect_ontology_snapshot("exit_blockage", seed=1)
    assert snap.semantic_labels
    assert snap.safety_states
    assert snap.scenario_id == "exit_blockage"


@pytest.mark.unit
def test_run_ontology_drift_detection_fast() -> None:
    report = run_ontology_drift_detection(
        scenarios=("exit_blockage",),
        seeds=(1, 2),
    )
    assert 0.0 <= report.ontology_stability <= 1.0
    assert 0.0 <= report.semantic_drift <= 1.0
    assert 0.0 <= report.recommendation_drift <= 1.0
    assert len(report.per_scenario) == 1


@pytest.mark.unit
def test_cross_version_skips_empty_registry(tmp_path: Path) -> None:
    from dualexis.core.version import get_version

    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "vocabulary_0.0.9.json").write_text(
        '{"version":"0.0.9","semantic_labels":[],"cells":{}}',
        encoding="utf-8",
    )
    report = run_ontology_drift_detection(
        scenarios=("exit_blockage",),
        seeds=(1,),
        versions=(get_version(), "0.0.9"),
        registry_dir=registry,
    )
    assert report.cross_version_semantic_drift == 0.0
    assert report.registry_warnings


@pytest.mark.unit
def test_export_ontology_drift(tmp_path: Path) -> None:
    report = run_ontology_drift_detection(
        scenarios=("exit_blockage",),
        seeds=(1, 2),
    )
    paths = export_ontology_drift_report(
        report,
        tmp_path / "drift",
        paper_sections=tmp_path / "sections",
    )
    assert (tmp_path / "drift" / "ontology_drift_report.json").is_file()
    assert Path(paths["section_tex"]).is_file()
