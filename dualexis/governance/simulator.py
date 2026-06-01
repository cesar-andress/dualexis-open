"""Simulated operator behavior for governance evaluation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from dualexis.governance.models import (
    ACTION_TO_STATE,
    GovernanceReviewCase,
    GovernanceState,
    OperatorAction,
    OperatorDecision,
    OperatorProfile,
)
from dualexis.orchestration.models import SeverityLevel

_CONTRIBUTION_TITLE = (
    "Human-AI Governance Layer for Safety Decision Support Systems"
)


@dataclass(frozen=True, slots=True)
class _ProfileBehavior:
    accept_if_correct: float
    accept_if_incorrect: float
    override_if_correct: float
    override_if_incorrect: float
    escalate_high_risk: float
    dismiss_low_severity: float
    latency_mean: float
    latency_std: float


_PROFILES: dict[OperatorProfile, _ProfileBehavior] = {
    OperatorProfile.CONSERVATIVE: _ProfileBehavior(
        accept_if_correct=0.92,
        accept_if_incorrect=0.38,
        override_if_correct=0.04,
        override_if_incorrect=0.18,
        escalate_high_risk=0.42,
        dismiss_low_severity=0.05,
        latency_mean=95.0,
        latency_std=28.0,
    ),
    OperatorProfile.BALANCED: _ProfileBehavior(
        accept_if_correct=0.85,
        accept_if_incorrect=0.55,
        override_if_correct=0.10,
        override_if_incorrect=0.28,
        escalate_high_risk=0.28,
        dismiss_low_severity=0.10,
        latency_mean=62.0,
        latency_std=20.0,
    ),
    OperatorProfile.AGGRESSIVE: _ProfileBehavior(
        accept_if_correct=0.72,
        accept_if_incorrect=0.22,
        override_if_correct=0.22,
        override_if_incorrect=0.52,
        escalate_high_risk=0.15,
        dismiss_low_severity=0.22,
        latency_mean=38.0,
        latency_std=14.0,
    ),
}


def _high_risk(case: GovernanceReviewCase) -> bool:
    return case.severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL} or case.requires_escalation


def _choose_action(case: GovernanceReviewCase, profile: OperatorProfile, rng: random.Random) -> OperatorAction:
    behavior = _PROFILES[profile]
    if case.severity == SeverityLevel.LOW and rng.random() < behavior.dismiss_low_severity:
        return OperatorAction.DISMISS

    if _high_risk(case) and rng.random() < behavior.escalate_high_risk:
        return OperatorAction.ESCALATE

    if case.ai_correct:
        if rng.random() < behavior.accept_if_correct:
            return OperatorAction.ACCEPT
        if rng.random() < behavior.override_if_correct / max(1e-6, 1.0 - behavior.accept_if_correct):
            return OperatorAction.OVERRIDE
        return OperatorAction.ESCALATE

    if rng.random() < behavior.accept_if_incorrect:
        return OperatorAction.ACCEPT
    if rng.random() < behavior.override_if_incorrect:
        return OperatorAction.OVERRIDE
    return OperatorAction.ESCALATE


def _sample_latency(behavior: _ProfileBehavior, rng: random.Random) -> float:
    draw = rng.gauss(behavior.latency_mean, behavior.latency_std)
    return max(5.0, draw)


def simulate_operator_decision(
    case: GovernanceReviewCase,
    *,
    profile: OperatorProfile,
    rng: random.Random,
    decided_at: datetime | None = None,
) -> OperatorDecision:
    """Apply one operator disposition to a pending governance case."""
    action = _choose_action(case, profile, rng)
    behavior = _PROFILES[profile]
    latency = _sample_latency(behavior, rng)
    timestamp = decided_at or datetime.now(tz=UTC)
    return OperatorDecision(
        case_id=case.case_id,
        profile=profile,
        prior_state=GovernanceState.PENDING_REVIEW,
        action=action,
        resulting_state=ACTION_TO_STATE[action],
        latency_seconds=round(latency, 2),
        decided_at=timestamp + timedelta(seconds=latency),
    )


def simulate_profile_decisions(
    cases: list[GovernanceReviewCase],
    *,
    profile: OperatorProfile,
    rng: random.Random,
) -> list[OperatorDecision]:
    """Simulate one decision per case for a single operator profile."""
    decisions: list[OperatorDecision] = []
    base_time = datetime.now(tz=UTC)
    for index, case in enumerate(cases):
        decisions.append(
            simulate_operator_decision(
                case,
                profile=profile,
                rng=rng,
                decided_at=base_time + timedelta(seconds=index * 0.01),
            )
        )
    return decisions


CONTRIBUTION_TITLE = _CONTRIBUTION_TITLE

__all__ = [
    "CONTRIBUTION_TITLE",
    "simulate_operator_decision",
    "simulate_profile_decisions",
]
