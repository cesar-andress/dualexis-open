"""Tests for formal Human-AI governance state machine."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import pytest

from dualexis.governance.formal_audit import export_governance_audit_report, run_formal_governance_audit
from dualexis.governance.formal_models import GovernanceMacroState, GovernanceTransitionSymbol
from dualexis.governance.models import (
    GovernanceReviewCase,
    GovernanceState,
    OperatorAction,
    OperatorDecision,
    OperatorProfile,
)
from dualexis.governance.state_machine import build_decision_trace, delta
from dualexis.orchestration.models import SeverityLevel


@pytest.mark.unit
def test_delta_issue_transition() -> None:
    target = delta(
        GovernanceMacroState.AI_RECOMMENDATION,
        GovernanceTransitionSymbol.ISSUE,
    )
    assert target == GovernanceMacroState.HUMAN_REVIEW


@pytest.mark.unit
def test_delta_escalate_to_institutional() -> None:
    target = delta(
        GovernanceMacroState.HUMAN_REVIEW,
        GovernanceTransitionSymbol.ESCALATE,
    )
    assert target == GovernanceMacroState.INSTITUTIONAL_ESCALATION


@pytest.mark.unit
def test_build_decision_trace_complete() -> None:
    now = datetime.now(tz=UTC)
    case = GovernanceReviewCase(
        case_id="case-1",
        scenario_id="exit_blockage",
        zone_id="cafeteria",
        severity=SeverityLevel.HIGH,
        ai_action="notify_staff",
        oracle_action="notify_staff",
        ai_confidence=0.8,
        ai_correct=True,
        requires_escalation=False,
        created_at=now,
    )
    decision = OperatorDecision(
        case_id="case-1",
        profile=OperatorProfile.BALANCED,
        action=OperatorAction.ACCEPT,
        resulting_state=GovernanceState.REVIEWED,
        latency_seconds=60.0,
        decided_at=now,
    )
    trace = build_decision_trace(case, decision)
    assert trace.trace_complete
    assert trace.terminal_macro_state == GovernanceMacroState.HUMAN_REVIEW
    assert len(trace.steps) >= 2


@pytest.mark.unit
def test_run_formal_governance_audit_fast() -> None:
    report = run_formal_governance_audit(fast=True, seed=1)
    assert report.graph.nodes
    assert report.graph.edges
    assert 0.0 <= report.metrics.governance_compliance_score <= 1.0
    assert report.trace_count > 0


@pytest.mark.unit
def test_export_formal_governance_audit(tmp_path: Path) -> None:
    report = run_formal_governance_audit(fast=True, seed=2)
    paths = export_governance_audit_report(
        report,
        tmp_path / "formal",
        paper_sections=tmp_path / "sections",
    )
    assert (tmp_path / "formal" / "governance_audit_report.json").is_file()
    assert Path(paths["section_tex"]).is_file()
