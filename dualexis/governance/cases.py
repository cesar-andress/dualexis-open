"""Collect and resample governance review cases from the DUALEXIS pipeline."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from uuid import uuid4

from dualexis.governance.models import GovernanceReviewCase
from dualexis.governance.oracle import (
    actions_align,
    oracle_action_for_scenario,
    requires_escalation,
)
from dualexis.orchestration.models import SeverityLevel
from dualexis.pipeline import run_pipeline
from dualexis.simulation.scenario import ScenarioId

DEFAULT_SCENARIOS: tuple[str, ...] = tuple(s.value for s in ScenarioId)
_DEFAULT_SEEDS: tuple[int, ...] = tuple(range(1, 21))


def _confidence_from_severity(severity: SeverityLevel, rng: random.Random) -> float:
    base = {
        SeverityLevel.LOW: 0.62,
        SeverityLevel.MEDIUM: 0.74,
        SeverityLevel.HIGH: 0.86,
        SeverityLevel.CRITICAL: 0.93,
    }[severity]
    return min(1.0, max(0.45, base + rng.uniform(-0.08, 0.08)))


def collect_pipeline_cases(
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    seeds: tuple[int, ...] = _DEFAULT_SEEDS,
) -> list[GovernanceReviewCase]:
    """Harvest review-required recommendations from pipeline runs."""
    cases: list[GovernanceReviewCase] = []
    for scenario in scenarios:
        oracle = oracle_action_for_scenario(scenario)
        for seed in seeds:
            output = run_pipeline(scenario, seed=seed)
            for rec in output.recommendations:
                if not rec.requires_human_review:
                    continue
                ai_correct = actions_align(rec.action, oracle)
                cases.append(
                    GovernanceReviewCase(
                        case_id=f"{scenario}-{seed}-{rec.recommendation_id.hex[:8]}",
                        scenario_id=scenario,
                        zone_id=rec.target_zone_id,
                        severity=rec.severity,
                        ai_action=rec.action,
                        oracle_action=oracle,
                        ai_confidence=_confidence_from_severity(rec.severity, random.Random(seed)),
                        ai_correct=ai_correct,
                        requires_escalation=requires_escalation(oracle, rec.severity),
                        created_at=rec.created_at,
                    )
                )
    return cases


def sample_review_cases(
    pool: list[GovernanceReviewCase],
    *,
    count: int,
    rng: random.Random,
) -> list[GovernanceReviewCase]:
    """Resample ``count`` cases with replacement from the pipeline pool."""
    if not pool:
        raise ValueError("case pool is empty; run collect_pipeline_cases first")
    sampled: list[GovernanceReviewCase] = []
    for index in range(count):
        base = rng.choice(pool)
        sampled.append(
            base.model_copy(
                update={
                    "case_id": f"sim-{index:04d}-{uuid4().hex[:6]}",
                    "ai_confidence": min(
                        1.0,
                        max(0.45, base.ai_confidence + rng.uniform(-0.12, 0.12)),
                    ),
                }
            )
        )
    return sampled


def build_case_pool(
    *,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    seeds: tuple[int, ...] = _DEFAULT_SEEDS,
) -> list[GovernanceReviewCase]:
    """Pipeline cases plus synthetic low-severity controls for distributional balance."""
    pool = collect_pipeline_cases(scenarios=scenarios, seeds=seeds)
    rng = random.Random(0)
    now = datetime.now(tz=UTC)
    for index, scenario in enumerate(scenarios):
        oracle = oracle_action_for_scenario(scenario)
        pool.append(
            GovernanceReviewCase(
                case_id=f"synthetic-control-{index}",
                scenario_id=scenario,
                zone_id="zone-control",
                severity=SeverityLevel.LOW,
                ai_action="monitor",
                oracle_action=oracle,
                ai_confidence=rng.uniform(0.55, 0.72),
                ai_correct=actions_align("monitor", oracle),
                requires_escalation=False,
                created_at=now,
            )
        )
    return pool


__all__ = [
    "DEFAULT_SCENARIOS",
    "build_case_pool",
    "collect_pipeline_cases",
    "sample_review_cases",
]
