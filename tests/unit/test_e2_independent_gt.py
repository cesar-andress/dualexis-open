"""E2 independent ground-truth pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.experiments.e2_independent_gt import (
    RESULTS_TEX_MARKERS,
    regenerate_ground_truth_yaml,
    sync_results_tex,
)
from dualexis.simulation.gt_rules import load_ground_truth_rules, rules_path_for
from dualexis.simulation.independent_labeler import build_independent_ground_truth
from dualexis.simulation.scenario import ScenarioId


@pytest.mark.unit
@pytest.mark.parametrize("scenario", [s.value for s in ScenarioId])
def test_gt_rules_yaml_exist(scenario: str) -> None:
    path = rules_path_for(ScenarioId(scenario))
    assert path.is_file()
    doc = load_ground_truth_rules(ScenarioId(scenario))
    assert doc.scenario_id.value == scenario


@pytest.mark.unit
def test_independent_labeler_has_no_event_generator_import() -> None:
    import ast

    module_path = Path(__file__).resolve().parents[2] / "dualexis/simulation/independent_labeler.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("event_generator" in name for name in imports)


@pytest.mark.unit
def test_regenerate_ground_truth_writes_yaml() -> None:
    paths = regenerate_ground_truth_yaml(["exit_blockage"])
    assert len(paths) == 1
    assert paths[0].name == "exit_blockage.yaml"
    content = paths[0].read_text(encoding="utf-8")
    assert content.startswith("scenario_id:")
    assert "e2_rules_pipeline_v1" in content


@pytest.mark.unit
def test_build_independent_matches_rules_exit_blockage() -> None:
    built = build_independent_ground_truth(ScenarioId.EXIT_BLOCKAGE, seed=0)
    labels = {label.semantic_label for label in built.labels}
    assert "exit_blockage" in labels or "exit_throughput_reduced" in labels


@pytest.mark.unit
def test_sync_results_tex_inserts_markers(tmp_path) -> None:
    results_tex = tmp_path / "results.tex"
    results_tex.write_text(
        "Intro paragraph.\n\n\\input{tables/baseline_results}\n",
        encoding="utf-8",
    )
    assert sync_results_tex(results_tex) is True
    updated = results_tex.read_text(encoding="utf-8")
    assert RESULTS_TEX_MARKERS[0] in updated
    assert "\\input{tables/e2_independent_gt}" in updated
    assert "\\input{tables/baseline_results}" in updated
