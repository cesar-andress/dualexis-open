"""Narrative completeness, consistency, and fidelity metrics."""

from __future__ import annotations

from dualexis.narratives.models import NarrativeBeat, NarrativeMetrics, NarrativeStageKind, NarrativeTrace
from dualexis.sssg.models import SafetyState
from dualexis.sssg.transitions import is_allowed_transition


REQUIRED_STAGES = frozenset(
    {
        NarrativeStageKind.EVIDENCE,
        NarrativeStageKind.STATE_CHANGE,
        NarrativeStageKind.RECOMMENDATION,
        NarrativeStageKind.GOVERNANCE,
    }
)


def compute_narrative_metrics(
    beats: list[NarrativeBeat],
    *,
    zone_id: str,
    record_states: list[tuple[int, SafetyState, SafetyState]],
    record_actions: list[str],
) -> NarrativeMetrics:
    """Compute completeness, consistency, and fidelity for one narrative."""
    completeness = _completeness(beats)
    consistency = _consistency(beats, record_states)
    fidelity = _fidelity(beats, zone_id, record_states, record_actions)
    return NarrativeMetrics(
        narrative_completeness=round(completeness, 4),
        narrative_consistency=round(consistency, 4),
        narrative_fidelity=round(fidelity, 4),
    )


def _completeness(beats: list[NarrativeBeat]) -> float:
    if not beats:
        return 0.0
    present = {beat.stage for beat in beats}
    covered = len(REQUIRED_STAGES & present)
    optional = 1.0 if NarrativeStageKind.STABILIZATION in present else 0.0
    return min(1.0, (covered / len(REQUIRED_STAGES)) * 0.85 + optional * 0.15)


def _consistency(
    beats: list[NarrativeBeat],
    record_states: list[tuple[int, SafetyState, SafetyState]],
) -> float:
    if len(beats) < 2:
        return 1.0 if beats else 0.0

    ticks = [beat.tick for beat in beats]
    monotonic = all(ticks[index] <= ticks[index + 1] for index in range(len(ticks) - 1))
    monotonic_score = 1.0 if monotonic else 0.5

    transition_ok = 0
    transition_total = 0
    state_by_tick = {tick: (from_s, to_s) for tick, from_s, to_s in record_states}
    for beat in beats:
        if beat.stage != NarrativeStageKind.STATE_CHANGE:
            continue
        pair = state_by_tick.get(beat.tick)
        if pair is None:
            continue
        transition_total += 1
        if is_allowed_transition(pair[0], pair[1]):
            transition_ok += 1

    transition_score = transition_ok / transition_total if transition_total else 1.0
    return min(1.0, 0.5 * monotonic_score + 0.5 * transition_score)


def _fidelity(
    beats: list[NarrativeBeat],
    zone_id: str,
    record_states: list[tuple[int, SafetyState, SafetyState]],
    record_actions: list[str],
) -> float:
    if not beats:
        return 0.0

    checks = 0
    passed = 0
    state_labels = {to_state.value.upper().replace("_", " ") for _, _, to_state in record_states}
    for beat in beats:
        if beat.zone_id != zone_id:
            continue
        checks += 1
        if beat.stage == NarrativeStageKind.STATE_CHANGE:
            if any(label in beat.text.upper() for label in state_labels):
                passed += 1
        elif beat.stage == NarrativeStageKind.RECOMMENDATION:
            if any(action.replace("_", " ") in beat.text.lower() for action in record_actions):
                passed += 1
            elif "review" in beat.text.lower():
                passed += 1
        elif beat.stage == NarrativeStageKind.GOVERNANCE:
            if any(
                token in beat.text.lower()
                for token in ("accepted", "override", "escalat", "dismiss")
            ):
                passed += 1
        elif beat.stage == NarrativeStageKind.EVIDENCE:
            passed += 1
        else:
            passed += 1

    return passed / checks if checks else 0.0


def aggregate_trace_metrics(traces: list[NarrativeTrace]) -> tuple[float, float, float]:
    if not traces:
        return 0.0, 0.0, 0.0
    n = len(traces)
    return (
        round(sum(t.metrics.narrative_completeness for t in traces) / n, 4),
        round(sum(t.metrics.narrative_consistency for t in traces) / n, 4),
        round(sum(t.metrics.narrative_fidelity for t in traces) / n, 4),
    )


__all__ = ["aggregate_trace_metrics", "compute_narrative_metrics"]
