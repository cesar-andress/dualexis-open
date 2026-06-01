"""SSSG evaluation metrics against independent ground-truth state sequences."""

from __future__ import annotations

from dataclasses import dataclass

from dualexis.simulation.ground_truth import GroundTruthLabel, ScenarioGroundTruth
from dualexis.sssg.evidence import semantic_label_to_safety_state
from dualexis.sssg.models import SafetyState, StateTransition, StateTransitionTrace


@dataclass(frozen=True)
class StateGraphMetrics:
    """Metric bundle for state-transition evaluation."""

    transition_precision: float
    transition_recall: float
    state_consistency: float
    causal_trace_completeness: float
    predicted_transitions: int
    expected_transitions: int
    matched_transitions: int


def _transition_key(zone_id: str, from_state: SafetyState, to_state: SafetyState) -> tuple[str, str, str]:
    return (zone_id, from_state.value, to_state.value)


def expected_transitions_from_ground_truth(
    ground_truth: ScenarioGroundTruth,
) -> list[tuple[str, SafetyState, SafetyState, int]]:
    """Derive expected state transitions from independent GT labels (per zone timeline)."""
    by_zone: dict[str, list[tuple[int, SafetyState]]] = {}
    for label in ground_truth.labels:
        state = semantic_label_to_safety_state(label.semantic_label)
        by_zone.setdefault(label.zone_id, []).append((label.tick, state))

    expected: list[tuple[str, SafetyState, SafetyState, int]] = []
    for zone_id, timeline in by_zone.items():
        timeline.sort(key=lambda item: item[0])
        current = SafetyState.NORMAL
        for tick, state in timeline:
            if state != current:
                expected.append((zone_id, current, state, tick))
                current = state
    return expected


def predicted_transition_tuples(
    trace: StateTransitionTrace,
) -> list[tuple[str, SafetyState, SafetyState, int]]:
    return [
        (t.zone_id, t.from_state, t.to_state, t.tick) for t in trace.transitions
    ]


def compute_state_graph_metrics(
    trace: StateTransitionTrace,
    ground_truth: ScenarioGroundTruth,
) -> StateGraphMetrics:
    """Compute transition precision/recall, state consistency, causal trace completeness."""
    expected = expected_transitions_from_ground_truth(ground_truth)
    predicted = predicted_transition_tuples(trace)

    expected_keys = {_transition_key(z, a, b) for z, a, b, _ in expected}
    predicted_keys = {_transition_key(z, a, b) for z, a, b, _ in predicted}

    matched = expected_keys & predicted_keys
    tp = len(matched)
    pred_n = len(predicted_keys)
    exp_n = len(expected_keys)

    transition_precision = tp / pred_n if pred_n else (1.0 if not exp_n else 0.0)
    transition_recall = tp / exp_n if exp_n else (1.0 if not pred_n else 0.0)

    # State consistency: final zone states vs. last GT label per zone
    last_gt: dict[str, SafetyState] = {}
    for label in sorted(ground_truth.labels, key=lambda label: label.tick):
        last_gt[label.zone_id] = semantic_label_to_safety_state(label.semantic_label)

    if not last_gt:
        state_consistency = 1.0
    else:
        agree = sum(
            1
            for zone_id, gt_state in last_gt.items()
            if trace.final_states.get(zone_id, SafetyState.NORMAL) == gt_state
        )
        state_consistency = agree / len(last_gt)

    # Causal trace completeness: transitions with >=1 causal edge id recorded
    if not trace.transitions:
        causal_trace_completeness = 1.0 if not expected else 0.0
    else:
        with_causal = sum(1 for t in trace.transitions if t.causal_edge_ids)
        causal_trace_completeness = with_causal / len(trace.transitions)

    return StateGraphMetrics(
        transition_precision=transition_precision,
        transition_recall=transition_recall,
        state_consistency=state_consistency,
        causal_trace_completeness=causal_trace_completeness,
        predicted_transitions=pred_n,
        expected_transitions=exp_n,
        matched_transitions=tp,
    )


def final_states_from_labels(labels: tuple[GroundTruthLabel, ...]) -> dict[str, SafetyState]:
    last: dict[str, SafetyState] = {}
    for label in sorted(labels, key=lambda item: item.tick):
        last[label.zone_id] = semantic_label_to_safety_state(label.semantic_label)
    return last


__all__ = [
    "StateGraphMetrics",
    "compute_state_graph_metrics",
    "expected_transitions_from_ground_truth",
    "predicted_transition_tuples",
]
