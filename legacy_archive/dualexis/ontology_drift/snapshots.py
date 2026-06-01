"""Collect ontology snapshots from simulation and pipeline artefacts."""

from __future__ import annotations

from dualexis.core.version import get_version
from dualexis.ontology_drift.models import OntologySnapshot
from dualexis.pipeline import run_pipeline
from dualexis.pipeline.config import PipelineRunConfig
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.runner import run_scenario
from dualexis.simulation.scenario import ScenarioId
from dualexis.sssg.runner import build_sssg_trace_from_scenario

ONTOLOGY_PIPELINE_CONFIG = PipelineRunConfig(
    enable_privacy_runtime=True,
    enable_temporal_graph=True,
    enable_explanation_layer=True,
    enable_sssg=True,
)


def collect_ontology_snapshot(
    scenario_id: str,
    *,
    seed: int,
    version: str | None = None,
) -> OntologySnapshot:
    """Harvest semantic labels, safety states, and recommendations for one run."""
    version_tag = version or get_version()
    scenario_enum = ScenarioId(scenario_id)

    gt = load_scenario_ground_truth(scenario_enum)
    label_set: set[str] = {label.semantic_label for label in gt.labels}

    simulation = run_scenario(scenario_id, seed=seed)
    for event in simulation.events:
        label_set.add(event.metadata.get("category", event.event_type.value))
        label_set.add(event.event_type.value)

    trace = build_sssg_trace_from_scenario(scenario_id, seed=seed)
    state_set: set[str] = {state.value for state in trace.final_states.values()}
    for transition in trace.transitions:
        state_set.add(transition.from_state.value)
        state_set.add(transition.to_state.value)

    output = run_pipeline(scenario_id, seed=seed, run_config=ONTOLOGY_PIPELINE_CONFIG)
    rec_set: set[str] = set()
    for rec in output.recommendations:
        rec_set.add(f"{rec.target_zone_id}:{rec.action}:{rec.severity.value}")

    if not rec_set:
        for zone_id, state in trace.final_states.items():
            if state.value != "normal":
                rec_set.add(f"{zone_id}:synthetic:{state.value}")

    for event in output.normalized_events:
        if event.metadata.get("category"):
            label_set.add(str(event.metadata["category"]))

    return OntologySnapshot(
        scenario_id=scenario_id,
        seed=seed,
        version=version_tag,
        semantic_labels=tuple(sorted(label_set)),
        safety_states=tuple(sorted(state_set)),
        recommendations=tuple(sorted(rec_set)),
    )


def collect_snapshot_grid(
    scenarios: tuple[str, ...],
    seeds: tuple[int, ...],
    *,
    version: str | None = None,
) -> tuple[OntologySnapshot, ...]:
    snapshots: list[OntologySnapshot] = []
    for scenario in scenarios:
        for seed in seeds:
            snapshots.append(
                collect_ontology_snapshot(scenario, seed=seed, version=version)
            )
    return tuple(snapshots)


__all__ = [
    "ONTOLOGY_PIPELINE_CONFIG",
    "collect_ontology_snapshot",
    "collect_snapshot_grid",
]
