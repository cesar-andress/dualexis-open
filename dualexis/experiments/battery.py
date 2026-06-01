"""Experimental battery execution for DUALEXIS."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from dualexis.evaluation import run_experiment
from dualexis.evaluation.results import ExperimentMetrics
from dualexis.experiments.config import ExperimentConfig
from dualexis.measurement import measure_all
from dualexis.measurement.models import MeasurementMetrics
from dualexis.pipeline import run_pipeline
from dualexis.simulation import run_scenario

BATTERY_DISCLAIMER = (
    "Reproducible experimental battery (synthetic inputs only). "
    "Reported values are measured scaffold outputs; no empirical conclusions are implied."
)


class BatteryResult(BaseModel):
    """Aggregated output from a full experimental battery run."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str = Field(min_length=1, max_length=64)
    scenario: str = Field(min_length=1, max_length=64)
    seed: int
    protocol: str = Field(min_length=1, max_length=64)
    config_path: str | None = None
    description: str = ""
    simulation_event_count: int = Field(ge=0)
    pipeline_event_count: int = Field(ge=0)
    pipeline_recommendation_count: int = Field(ge=0)
    experiment_metrics: ExperimentMetrics
    measurement_metrics: MeasurementMetrics
    privacy_compliant: bool
    privacy_validation_passed: bool
    robustness_modality_drop_tolerance: float = Field(ge=0.0, le=1.0)
    deterministic_reproducibility_score: float = Field(ge=0.0, le=1.0)
    generated_at: datetime
    disclaimer: str = BATTERY_DISCLAIMER


def run_battery(
    config: ExperimentConfig,
    *,
    config_path: str | None = None,
    seed: int | None = None,
) -> BatteryResult:
    """Run simulation, pipeline, metrics, privacy validation, and robustness probes."""
    effective = config.model_copy(update={"seed": seed}) if seed is not None else config
    simulation = run_scenario(effective.scenario, seed=effective.seed)
    pipeline_output = run_pipeline(effective.scenario, seed=effective.seed)
    experiment_report = run_experiment(
        effective.scenario,
        effective.protocol,
        seed=effective.seed,
    )
    measurements = measure_all(
        effective.scenario,
        seed=effective.seed,
        runs=effective.latency_runs,
        drop_modality=effective.drop_modality,
    )

    privacy_compliant = pipeline_output.privacy_report.policy_compliant
    privacy_validation_passed = (
        privacy_compliant
        and experiment_report.metrics.privacy_violation_count == 0
        and measurements.scenario_report.metrics.privacy_violation_count == 0
    )

    return BatteryResult(
        experiment_id=effective.experiment_id,
        scenario=effective.scenario,
        seed=effective.seed,
        protocol=effective.protocol,
        config_path=config_path,
        description=effective.description,
        simulation_event_count=len(simulation.events),
        pipeline_event_count=len(pipeline_output.normalized_events),
        pipeline_recommendation_count=len(pipeline_output.recommendations),
        experiment_metrics=experiment_report.metrics,
        measurement_metrics=measurements.scenario_report.metrics,
        privacy_compliant=privacy_compliant,
        privacy_validation_passed=privacy_validation_passed,
        robustness_modality_drop_tolerance=(
            measurements.robustness_report.metrics.modality_drop_tolerance
        ),
        deterministic_reproducibility_score=(
            measurements.scenario_report.metrics.deterministic_reproducibility_score
        ),
        generated_at=datetime.now(tz=UTC),
    )


__all__ = ["BATTERY_DISCLAIMER", "BatteryResult", "run_battery"]
