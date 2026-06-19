"""Tests for coupling-controlled PAR decomposition experiment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dualexis.evaluation.procedural_agreement import (
    metrics_from_label_keys,
    procedural_agreement_metrics,
)
from dualexis.semantic_events.models import EventType
from dualexis.simulation.ground_truth import GroundTruthLabel, ScenarioGroundTruth
from dualexis.simulation.scenario import ScenarioId
from dualexis.experiments.coupling_controlled_par import run_coupling_controlled_par_experiment
from dualexis.simulation import run_scenario
from dualexis.simulation.coupling_perturbation import (
    CouplingChannel,
    CouplingPerturbationConfig,
)
from dualexis.simulation.emission_mode import EmissionMode
from dualexis.experiments.coupling_controlled_par import run_coupling_controlled_scenario


@pytest.mark.unit
def test_lambda_zero_zone_permutation_matches_decoupled_benchmark() -> None:
    baseline = run_scenario("exit_blockage", seed=17, emission_mode=EmissionMode.DECOUPLED)
    baseline_events = tuple(e for e in baseline.events if e.source.value == "simulator")
    baseline_par = procedural_agreement_metrics(baseline_events, baseline.ground_truth).par

    config = CouplingPerturbationConfig(
        channel=CouplingChannel.ZONE_PERMUTATION,
        lambda_=0.0,
        seed=17,
    )
    perturbed_events, gt, _ = run_coupling_controlled_scenario("exit_blockage", seed=17, config=config)
    perturbed_par = procedural_agreement_metrics(perturbed_events, gt).par
    assert perturbed_par == pytest.approx(baseline_par, abs=1e-6)


@pytest.mark.unit
def test_delta_proc_toy_case() -> None:
    gt = ScenarioGroundTruth(
        scenario_id=ScenarioId.NORMAL_FLOW,
        primary_label="normal_flow",
        labels=(
            GroundTruthLabel(
                scenario_id=ScenarioId.NORMAL_FLOW,
                tick=1,
                zone_id="cafeteria",
                semantic_label="a",
                expected_event_type=EventType.NORMAL_FLOW,
            ),
            GroundTruthLabel(
                scenario_id=ScenarioId.NORMAL_FLOW,
                tick=1,
                zone_id="exit-lobby",
                semantic_label="b",
                expected_event_type=EventType.NORMAL_FLOW,
            ),
        ),
    )
    matching = [("cafeteria", "a"), ("exit-lobby", "b")]
    shuffled_labels = ["b", "a"]
    permuted = [("cafeteria", shuffled_labels[0]), ("exit-lobby", shuffled_labels[1])]
    par_match = metrics_from_label_keys(matching, gt).par
    par_shuffle = metrics_from_label_keys(permuted, gt).par
    delta = round(par_match - par_shuffle, 4)
    assert par_match == 1.0
    assert par_shuffle < par_match
    assert delta > 0


@pytest.mark.unit
def test_coupling_controlled_experiment_writes_outputs(tmp_path: Path) -> None:
    report = run_coupling_controlled_par_experiment(
        output_dir=tmp_path,
        scenarios=("normal_flow",),
        seeds=(1, 2),
        lambdas=(0.0, 1.0),
        channels=(CouplingChannel.ZONE_PERMUTATION,),
        chance_permutations=50,
    )
    assert (tmp_path / "coupling_controlled_par.csv").is_file()
    assert (tmp_path / "coupling_controlled_par.json").is_file()
    assert (tmp_path / "coupling_controlled_par.tex").is_file()
    assert (tmp_path / "coupling_controlled_par_by_run.csv").is_file()
    payload = json.loads((tmp_path / "coupling_controlled_par.json").read_text())
    assert payload["run_count"] == 4
    assert report.aggregate_rows
