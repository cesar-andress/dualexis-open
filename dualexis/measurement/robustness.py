"""Robustness measurement under modality dropout."""

from __future__ import annotations

from dualexis.measurement.latency import run_instrumented_pipeline


def measure_modality_drop_tolerance(
    scenario_name: str,
    *,
    seed: int = 42,
    drop_modality: str = "audio",
) -> float:
    """Score pipeline resilience when a modality is dropped (1.0 = no degradation)."""
    baseline = run_instrumented_pipeline(scenario_name, seed=seed)
    dropped = run_instrumented_pipeline(
        scenario_name,
        seed=seed,
        drop_modality=drop_modality,
    )

    baseline_events = len(baseline.output.normalized_events)
    dropped_events = len(dropped.output.normalized_events)
    if baseline_events == 0:
        return 1.0 if dropped_events == 0 else 0.0

    event_ratio = min(1.0, dropped_events / baseline_events)

    baseline_recs = len(baseline.output.recommendations)
    dropped_recs = len(dropped.output.recommendations)
    if baseline_recs == 0:
        rec_ratio = 1.0 if dropped_recs == 0 else 0.5
    else:
        rec_ratio = min(1.0, dropped_recs / baseline_recs)

    privacy_ok = (
        dropped.output.privacy_report.policy_compliant
        == baseline.output.privacy_report.policy_compliant
    )
    privacy_factor = 1.0 if privacy_ok else 0.0

    return round((event_ratio + rec_ratio + privacy_factor) / 3.0, 6)


__all__ = ["measure_modality_drop_tolerance"]
