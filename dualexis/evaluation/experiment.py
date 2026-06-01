"""Q1-oriented experiment runner for DUALEXIS evaluation."""

from __future__ import annotations

from datetime import UTC, datetime

from dualexis.evaluation.metrics import compute_experiment_metrics
from dualexis.evaluation.protocol import (
    ExperimentProtocolId,
    UnknownProtocolError,
    execute_protocol,
    get_protocol,
)
from dualexis.evaluation.results import (
    SCAFFOLD_DISCLAIMER,
    ExperimentReport,
    format_experiment_summary,
)
from dualexis.simulation.runner import run_scenario
from dualexis.simulation.scenario import UnknownScenarioError


def run_experiment(
    scenario_name: str,
    protocol_name: str,
    *,
    seed: int = 42,
    notes: str = "",
) -> ExperimentReport:
    """Run simulation + protocol and return a reproducible experiment report."""
    get_protocol(protocol_name)
    simulation = run_scenario(scenario_name, seed=seed)
    protocol_id = ExperimentProtocolId(protocol_name)
    execution = execute_protocol(protocol_id, simulation, scenario_name=scenario_name)
    metrics = compute_experiment_metrics(execution, simulation.ground_truth)

    merged_notes = notes.strip() or SCAFFOLD_DISCLAIMER
    return ExperimentReport(
        scenario_name=scenario_name,
        protocol_id=protocol_id.value,
        seed=seed,
        metrics=metrics,
        generated_at=datetime.now(tz=UTC),
        notes=merged_notes,
    )


__all__ = [
    "ExperimentReport",
    "UnknownProtocolError",
    "UnknownScenarioError",
    "format_experiment_summary",
    "run_experiment",
]
