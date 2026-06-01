"""Measurement orchestration for DUALEXIS CLI commands."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from dualexis.measurement.latency import (
    LatencyAggregate,
    StageTimings,
    measure_latency,
    run_instrumented_pipeline,
)
from dualexis.measurement.models import (
    CombinedMeasurementReport,
    MeasurementKind,
    MeasurementMetrics,
    MeasurementReport,
)
from dualexis.measurement.privacy import extract_privacy_metrics
from dualexis.measurement.robustness import measure_modality_drop_tolerance
from dualexis.pipeline import run_pipeline
from dualexis.pipeline.models import PipelineOutput


def _fingerprint_output(output: PipelineOutput) -> str:
    """Stable hash of pipeline outputs for reproducibility scoring."""
    payload = {
        "event_count": len(output.normalized_events),
        "recommendation_count": len(output.recommendations),
        "graph_updates": len(output.graph_updates),
        "audit_records": len(output.audit_records),
        "policy_compliant": output.privacy_report.policy_compliant,
        "privacy_violations": len(output.privacy_report.violations),
        "event_types": sorted(event.event_type.value for event in output.normalized_events),
        "severities": sorted(event.severity.value for event in output.normalized_events),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_reproducibility_score(scenario_name: str, *, seed: int) -> float:
    """Return 1.0 when two pipeline runs with the same seed produce identical fingerprints."""
    first = run_pipeline(scenario_name, seed=seed)
    second = run_pipeline(scenario_name, seed=seed)
    return 1.0 if _fingerprint_output(first) == _fingerprint_output(second) else 0.0


def _build_metrics(
    output: PipelineOutput,
    timings: StageTimings,
    *,
    modality_drop_tolerance: float = 1.0,
    deterministic_reproducibility_score: float = 1.0,
) -> MeasurementMetrics:
    privacy = extract_privacy_metrics(output)
    return MeasurementMetrics(
        end_to_end_latency_ms=timings.end_to_end_latency_ms,
        event_generation_latency_ms=timings.event_generation_latency_ms,
        fusion_latency_ms=timings.fusion_latency_ms,
        graph_update_latency_ms=timings.graph_update_latency_ms,
        reasoning_latency_ms=timings.reasoning_latency_ms,
        recommendation_latency_ms=timings.recommendation_latency_ms,
        number_of_events=len(output.normalized_events),
        number_of_recommendations=len(output.recommendations),
        privacy_violation_count=int(privacy["privacy_violation_count"]),
        raw_media_retention_score=float(privacy["raw_media_retention_score"]),
        personal_data_exposure_score=float(privacy["personal_data_exposure_score"]),
        human_review_compliance_rate=float(privacy["human_review_compliance_rate"]),
        modality_drop_tolerance=modality_drop_tolerance,
        deterministic_reproducibility_score=deterministic_reproducibility_score,
    )


def _report(
    kind: MeasurementKind,
    scenario_name: str,
    *,
    seed: int,
    runs: int,
    metrics: MeasurementMetrics,
    metadata: dict[str, str] | None = None,
) -> MeasurementReport:
    return MeasurementReport(
        kind=kind,
        scenario=scenario_name,
        seed=seed,
        runs=runs,
        metrics=metrics,
        generated_at=datetime.now(tz=UTC),
        metadata=metadata or {},
    )


def measure_scenario(scenario_name: str, *, seed: int = 42) -> MeasurementReport:
    """Collect full metrics for a single scenario run."""
    instrumented = run_instrumented_pipeline(scenario_name, seed=seed)
    reproducibility = compute_reproducibility_score(scenario_name, seed=seed)
    metrics = _build_metrics(
        instrumented.output,
        instrumented.timings,
        deterministic_reproducibility_score=reproducibility,
    )
    return _report(MeasurementKind.SCENARIO, scenario_name, seed=seed, runs=1, metrics=metrics)


def measure_latency_report(
    scenario_name: str,
    *,
    seed: int = 42,
    runs: int = 1,
) -> MeasurementReport:
    """Collect latency-focused metrics averaged over repeated runs."""
    aggregate: LatencyAggregate = measure_latency(scenario_name, seed=seed, runs=runs)
    output = run_pipeline(scenario_name, seed=seed)
    reproducibility = compute_reproducibility_score(scenario_name, seed=seed)
    metrics = _build_metrics(
        output,
        aggregate.timings,
        deterministic_reproducibility_score=reproducibility,
    )
    return _report(
        MeasurementKind.LATENCY,
        scenario_name,
        seed=seed,
        runs=runs,
        metrics=metrics,
        metadata={"latency_runs": str(runs)},
    )


def measure_privacy_report(scenario_name: str, *, seed: int = 42) -> MeasurementReport:
    """Collect privacy-focused metrics for a scenario run."""
    instrumented = run_instrumented_pipeline(scenario_name, seed=seed)
    reproducibility = compute_reproducibility_score(scenario_name, seed=seed)
    metrics = _build_metrics(
        instrumented.output,
        instrumented.timings,
        deterministic_reproducibility_score=reproducibility,
    )
    return _report(MeasurementKind.PRIVACY, scenario_name, seed=seed, runs=1, metrics=metrics)


def measure_robustness_report(
    scenario_name: str,
    *,
    seed: int = 42,
    runs: int = 1,
    drop_modality: str = "audio",
) -> MeasurementReport:
    """Collect robustness metrics under modality dropout."""
    instrumented = run_instrumented_pipeline(scenario_name, seed=seed)
    tolerance = measure_modality_drop_tolerance(
        scenario_name,
        seed=seed,
        drop_modality=drop_modality,
    )
    reproducibility = compute_reproducibility_score(scenario_name, seed=seed)
    metrics = _build_metrics(
        instrumented.output,
        instrumented.timings,
        modality_drop_tolerance=tolerance,
        deterministic_reproducibility_score=reproducibility,
    )
    return _report(
        MeasurementKind.ROBUSTNESS,
        scenario_name,
        seed=seed,
        runs=runs,
        metrics=metrics,
        metadata={"drop_modality": drop_modality, "robustness_runs": str(runs)},
    )


def measure_all(
    scenario_name: str,
    *,
    seed: int = 42,
    runs: int = 1,
    drop_modality: str = "audio",
) -> CombinedMeasurementReport:
    """Run scenario, latency, privacy, and robustness measurements."""
    return CombinedMeasurementReport(
        scenario=scenario_name,
        seed=seed,
        runs=runs,
        scenario_report=measure_scenario(scenario_name, seed=seed),
        latency_report=measure_latency_report(scenario_name, seed=seed, runs=runs),
        privacy_report=measure_privacy_report(scenario_name, seed=seed),
        robustness_report=measure_robustness_report(
            scenario_name,
            seed=seed,
            runs=runs,
            drop_modality=drop_modality,
        ),
        generated_at=datetime.now(tz=UTC),
    )


def format_measurement_summary(report: MeasurementReport) -> str:
    """Human-readable one-line summary for CLI output."""
    metrics = report.metrics
    return (
        f"kind={report.kind.value} scenario={report.scenario} seed={report.seed} "
        f"events={metrics.number_of_events} e2e_ms={metrics.end_to_end_latency_ms:.2f} "
        f"privacy_violations={metrics.privacy_violation_count}"
    )


__all__ = [
    "CombinedMeasurementReport",
    "MeasurementReport",
    "format_measurement_summary",
    "measure_all",
    "measure_latency_report",
    "measure_privacy_report",
    "measure_robustness_report",
    "measure_scenario",
]
