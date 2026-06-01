"""Tests for Human-AI governance framework."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.governance.graph import build_governance_graph_dot
from dualexis.governance.metrics import compute_bias_risks, compute_profile_metrics
from dualexis.governance.models import (
    ACTION_TO_STATE,
    GovernanceState,
    OperatorAction,
    OperatorProfile,
)
from dualexis.governance.simulator import simulate_operator_decision
from dualexis.governance.evaluation import run_governance_evaluation
from dualexis.governance.cases import sample_review_cases, build_case_pool
import random


@pytest.mark.unit
def test_governance_state_transitions() -> None:
    assert ACTION_TO_STATE[OperatorAction.ACCEPT] == GovernanceState.REVIEWED
    assert ACTION_TO_STATE[OperatorAction.OVERRIDE] == GovernanceState.OVERRIDDEN


@pytest.mark.unit
def test_governance_graph_contains_states() -> None:
    dot = build_governance_graph_dot()
    for state in GovernanceState:
        assert state.value in dot


@pytest.mark.unit
def test_simulate_decision_bounded_latency() -> None:
    pool = build_case_pool(seeds=(1,))
    case = pool[0]
    decision = simulate_operator_decision(
        case,
        profile=OperatorProfile.BALANCED,
        rng=random.Random(1),
    )
    assert decision.latency_seconds >= 5.0
    assert decision.prior_state == GovernanceState.PENDING_REVIEW


@pytest.mark.unit
def test_run_governance_evaluation_fast(tmp_path: Path) -> None:
    report = run_governance_evaluation(
        output_dir=tmp_path / "gov",
        paper_tables=tmp_path / "tables",
        paper_sections=tmp_path / "sections",
        fast=True,
        seed=1,
    )
    assert report.simulation_iterations == 50
    assert len(report.profile_metrics) == 3
    assert (tmp_path / "gov" / "governance_metrics.csv").is_file()
    assert (tmp_path / "tables" / "governance_metrics.tex").is_file()
    assert (tmp_path / "sections" / "governance_evaluation.tex").is_file()


@pytest.mark.unit
def test_bias_risks_bounded() -> None:
    pool = build_case_pool(seeds=(1, 2))
    cases = sample_review_cases(pool, count=20, rng=random.Random(0))
    decisions = []
    for case in cases:
        decisions.append(
            simulate_operator_decision(case, profile=OperatorProfile.BALANCED, rng=random.Random(1))
        )
    risks = compute_bias_risks(decisions, {c.case_id: c for c in cases})
    assert 0.0 <= risks.automation_bias_risk <= 1.0
    assert 0.0 <= risks.over_reliance_risk <= 1.0
    metrics = compute_profile_metrics(decisions, cases, profile=OperatorProfile.BALANCED)
    assert metrics.acceptance_rate + metrics.override_rate <= 1.01
