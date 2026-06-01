"""Tests for Semantic Safety State Graph (SSSG)."""

from __future__ import annotations

import pytest

from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.scenario import ScenarioId
from dualexis.sssg.evidence import semantic_label_to_safety_state
from dualexis.sssg.metrics import compute_state_graph_metrics, expected_transitions_from_ground_truth
from dualexis.sssg.models import SafetyState
from dualexis.sssg.runner import build_sssg_trace_from_scenario, evaluate_sssg_trace
from dualexis.sssg.transitions import (
    ALLOWED_TRANSITIONS,
    DOCUMENTED_TRANSITION_CHAINS,
    is_allowed_transition,
    resolve_transition,
)


@pytest.mark.unit
def test_documented_transition_chains_allowed() -> None:
    for pair in DOCUMENTED_TRANSITION_CHAINS:
        assert pair in ALLOWED_TRANSITIONS
        assert is_allowed_transition(pair[0], pair[1])


@pytest.mark.unit
def test_resolve_transition_blocks_invalid_jump() -> None:
    result = resolve_transition(SafetyState.NORMAL, SafetyState.EVACUATION_CANDIDATE)
    assert result == SafetyState.EVACUATION_CANDIDATE


@pytest.mark.unit
def test_semantic_label_mapping() -> None:
    assert semantic_label_to_safety_state("multimodal_conflict") == SafetyState.MULTI_MODAL_CONFLICT
    assert semantic_label_to_safety_state("exit_throughput_reduced") == SafetyState.EXIT_IMPAIRMENT


@pytest.mark.unit
def test_build_sssg_trace_exit_blockage() -> None:
    trace = build_sssg_trace_from_scenario("exit_blockage", seed=1)
    assert trace.scenario_id == "exit_blockage"
    assert trace.transitions
    assert any(t.to_state == SafetyState.EXIT_IMPAIRMENT for t in trace.transitions)


@pytest.mark.unit
def test_state_graph_metrics_bounded() -> None:
    trace, metrics = evaluate_sssg_trace("exit_blockage", seed=1)
    gt = load_scenario_ground_truth(ScenarioId.EXIT_BLOCKAGE)
    expected = expected_transitions_from_ground_truth(gt)
    assert expected
    recomputed = compute_state_graph_metrics(trace, gt)
    assert 0.0 <= recomputed.transition_precision <= 1.0
    assert 0.0 <= recomputed.causal_trace_completeness <= 1.0
    assert metrics.predicted_transitions == recomputed.predicted_transitions


@pytest.mark.unit
def test_transition_explanation_mentions_state_change() -> None:
    trace = build_sssg_trace_from_scenario("exit_blockage", seed=1)
    sample = trace.transitions[0]
    assert "State changed from" in sample.explanation
