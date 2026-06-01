"""NearMissDetector — identify near-miss governance dispositions."""

from __future__ import annotations

from collections import Counter

from dualexis.governance.formal_models import (
    GovernanceDecisionTrace,
    GovernanceTransitionSymbol,
)
from dualexis.governance.models import OperatorAction
from dualexis.institutional_memory.models import NearMissPattern


class NearMissDetector:
    """Detect near-miss patterns from historical governance traces."""

    def detect(self, traces: list[GovernanceDecisionTrace]) -> list[NearMissPattern]:
        if not traces:
            return []

        buckets: Counter[tuple[str, str, str, str, bool, bool, bool]] = Counter()
        samples: dict[tuple[str, str, str, str, bool, bool, bool], GovernanceDecisionTrace] = {}

        for trace in traces:
            action = _terminal_action(trace)
            near_type = _classify_near_miss(trace, action)
            if near_type is None:
                continue
            key = (
                trace.scenario_id,
                trace.zone_id,
                near_type,
                action,
                trace.ai_correct,
                trace.policy_compliant,
                trace.requires_escalation,
            )
            buckets[key] += 1
            samples[key] = trace

        patterns: list[NearMissPattern] = []
        for index, (key, count) in enumerate(buckets.most_common()):
            scenario_id, zone_id, near_type, action, ai_correct, compliant, _req = key
            trace = samples[key]
            patterns.append(
                NearMissPattern(
                    pattern_id=f"nm-{index:04d}",
                    scenario_id=scenario_id,
                    zone_id=zone_id,
                    near_miss_type=near_type,
                    description=_describe_near_miss(near_type, action, ai_correct, compliant),
                    occurrence_count=count,
                    ai_correct=ai_correct,
                    operator_action=action,
                    policy_compliant=compliant,
                )
            )
        return patterns


def _classify_near_miss(trace: GovernanceDecisionTrace, action: str) -> str | None:
    if not trace.ai_correct and action == OperatorAction.ACCEPT.value:
        return "incorrect_ai_accepted"
    if trace.requires_escalation and action != OperatorAction.ESCALATE.value:
        if trace.terminal_macro_state.value != "institutional_escalation":
            return "escalation_required_not_escalated"
    if not trace.ai_correct and action == OperatorAction.DISMISS.value:
        return "incorrect_ai_dismissed"
    return None


def _terminal_action(trace: GovernanceDecisionTrace) -> str:
    for step in reversed(trace.steps):
        if step.symbol.value in {"accept", "override", "escalate", "dismiss"}:
            return step.symbol.value
    return "unknown"


def _describe_near_miss(
    near_type: str,
    action: str,
    ai_correct: bool,
    compliant: bool,
) -> str:
    templates = {
        "incorrect_ai_accepted": (
            f"Operator {action}ed AI advice that disagreed with oracle; policy risk."
        ),
        "escalation_required_not_escalated": (
            "Escalation was required but disposition did not reach institutional review."
        ),
        "incorrect_ai_dismissed": "Incorrect AI advice dismissed without corrective override.",
        "missed_override_opportunity": (
            "Incorrect AI advice accepted without override despite review window."
        ),
    }
    base = templates.get(near_type, "Near-miss governance disposition.")
    if compliant:
        return base + " Recorded as policy-compliant in harness."
    return base + " Policy non-compliance flagged."


__all__ = ["NearMissDetector"]
