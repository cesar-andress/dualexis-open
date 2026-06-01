"""Governance KPIs and Human-AI reliance risk metrics."""

from __future__ import annotations

from collections import defaultdict

from dualexis.governance.models import (
    BiasRiskMetrics,
    GovernanceReviewCase,
    GovernanceState,
    OperatorDecision,
    OperatorProfile,
    ProfileGovernanceMetrics,
)


def _case_index(cases: list[GovernanceReviewCase]) -> dict[str, GovernanceReviewCase]:
    return {case.case_id: case for case in cases}


def compute_profile_metrics(
    decisions: list[OperatorDecision],
    cases: list[GovernanceReviewCase],
    *,
    profile: OperatorProfile,
) -> ProfileGovernanceMetrics:
    """Aggregate acceptance, override, escalation, latency, and bias risks."""
    by_case = _case_index(cases)
    total = len(decisions) or 1
    reviewed = sum(1 for d in decisions if d.resulting_state == GovernanceState.REVIEWED)
    overridden = sum(1 for d in decisions if d.resulting_state == GovernanceState.OVERRIDDEN)
    escalated = sum(1 for d in decisions if d.resulting_state == GovernanceState.ESCALATED)
    dismissed = sum(1 for d in decisions if d.resulting_state == GovernanceState.DISMISSED)
    latencies = [d.latency_seconds for d in decisions]

    bias = compute_bias_risks(decisions, by_case)
    return ProfileGovernanceMetrics(
        profile=profile,
        decision_count=len(decisions),
        acceptance_rate=round(reviewed / total, 4),
        override_rate=round(overridden / total, 4),
        escalation_rate=round(escalated / total, 4),
        dismissal_rate=round(dismissed / total, 4),
        mean_review_latency_seconds=round(sum(latencies) / total, 2),
        bias_risks=bias,
    )


def compute_bias_risks(
    decisions: list[OperatorDecision],
    cases_by_id: dict[str, GovernanceReviewCase],
) -> BiasRiskMetrics:
    """
    Estimate automation bias, under-reliance, and over-reliance risks.

    - automation_bias_risk: excess acceptance when AI is wrong and confidence is high
    - under_reliance_risk: override/escalate when AI matches oracle
    - over_reliance_risk: accept when AI does not match oracle
    """
    high_conf_wrong_accept = 0
    high_conf_wrong_total = 0
    low_conf_wrong_accept = 0
    low_conf_wrong_total = 0

    under_events = 0
    under_total = 0
    over_accept = 0
    over_total = 0

    for decision in decisions:
        case = cases_by_id.get(decision.case_id)
        if case is None:
            continue
        high_conf = case.ai_confidence >= 0.8
        accepted = decision.resulting_state == GovernanceState.REVIEWED
        overridden = decision.resulting_state in {
            GovernanceState.OVERRIDDEN,
            GovernanceState.ESCALATED,
        }

        if not case.ai_correct:
            over_total += 1
            if accepted:
                over_accept += 1
            if high_conf:
                high_conf_wrong_total += 1
                if accepted:
                    high_conf_wrong_accept += 1
            else:
                low_conf_wrong_total += 1
                if accepted:
                    low_conf_wrong_accept += 1

        if case.ai_correct:
            under_total += 1
            if overridden:
                under_events += 1

    automation = 0.0
    if high_conf_wrong_total and low_conf_wrong_total:
        p_high = high_conf_wrong_accept / high_conf_wrong_total
        p_low = low_conf_wrong_accept / low_conf_wrong_total
        automation = max(0.0, min(1.0, p_high - p_low))
    elif high_conf_wrong_total:
        automation = high_conf_wrong_accept / high_conf_wrong_total

    under = under_events / under_total if under_total else 0.0
    over = over_accept / over_total if over_total else 0.0

    return BiasRiskMetrics(
        automation_bias_risk=round(automation, 4),
        under_reliance_risk=round(under, 4),
        over_reliance_risk=round(over, 4),
    )


def aggregate_metrics_by_profile(
    decisions: list[OperatorDecision],
    cases: list[GovernanceReviewCase],
) -> tuple[ProfileGovernanceMetrics, ...]:
    """Group decisions by profile and compute metrics."""
    grouped: dict[OperatorProfile, list[OperatorDecision]] = defaultdict(list)
    for decision in decisions:
        grouped[decision.profile].append(decision)
    return tuple(
        compute_profile_metrics(grouped[profile], cases, profile=profile)
        for profile in OperatorProfile
    )


__all__ = [
    "aggregate_metrics_by_profile",
    "compute_bias_risks",
    "compute_profile_metrics",
]
