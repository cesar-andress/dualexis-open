"""Tests for decoupled benchmark, manifest verification, and emission decoupling."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from dualexis.evaluation.procedural_agreement import (
    aggregate_micro_rates,
    procedural_agreement_metrics,
)
from dualexis.experiments.benchmark_manifest import (
    load_benchmark_manifest,
    verify_benchmark_manifest,
)
from dualexis.experiments.decoupled_benchmark import run_decoupled_benchmark, run_shared_spec_regression
from dualexis.experiments.empirical_battery import DEFAULT_SEEDS, PAPER_SCENARIOS
from dualexis.simulation import run_scenario
from dualexis.simulation.emission_mode import EmissionMode

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_metric_heuristic_emitter_does_not_import_gt_rules() -> None:
    module_path = ROOT / "dualexis/simulation/metric_heuristic_emitter.py"
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
    assert not any("gt_rules" in (name or "") for name in imports)


@pytest.mark.unit
def test_benchmark_manifest_hashes_verify() -> None:
    result = verify_benchmark_manifest()
    assert result.ok, result.mismatches


@pytest.mark.unit
def test_aggregate_par_within_manifest_band() -> None:
    manifest = load_benchmark_manifest()
    metrics = []
    for scenario in PAPER_SCENARIOS:
        for seed in DEFAULT_SEEDS:
            result = run_scenario(scenario, seed=seed, emission_mode=EmissionMode.DECOUPLED)
            sim_events = tuple(e for e in result.events if e.source.value == "simulator")
            metrics.append(procedural_agreement_metrics(sim_events, result.ground_truth))
    aggregate = aggregate_micro_rates(metrics)
    low, high = manifest.target_par_band
    assert low <= aggregate.par <= high


@pytest.mark.unit
def test_shared_spec_regression_near_perfect_agreement() -> None:
    for scenario in PAPER_SCENARIOS:
        pars = []
        for seed in (1, 7, 17):
            result = run_scenario(scenario, seed=seed, emission_mode=EmissionMode.SHARED_SPEC)
            sim_events = tuple(e for e in result.events if e.source.value == "simulator")
            pars.append(procedural_agreement_metrics(sim_events, result.ground_truth).par)
        assert min(pars) >= 0.99


@pytest.mark.unit
def test_decoupled_benchmark_writes_expected_artefacts(tmp_path: Path) -> None:
    report = run_decoupled_benchmark(
        output_dir=tmp_path,
        scenarios=("normal_flow", "exit_blockage"),
        seeds=(1, 2),
        leakage_fast=True,
    )
    assert (tmp_path / "procedural_agreement_results.csv").is_file()
    assert (tmp_path / "procedural_agreement_summary.json").is_file()
    assert (tmp_path / "procedural_agreement.tex").is_file()
    summary = json.loads((tmp_path / "procedural_agreement_summary.json").read_text())
    assert summary["aggregate_par"] == pytest.approx(report.aggregate.par)


@pytest.mark.unit
def test_shared_spec_regression_writes_expected_artefacts(tmp_path: Path) -> None:
    run_shared_spec_regression(
        output_dir=tmp_path,
        scenarios=("normal_flow",),
        seeds=(1,),
    )
    assert (tmp_path / "shared_spec_regression.json").is_file()
    assert (tmp_path / "shared_spec_regression.tex").is_file()
