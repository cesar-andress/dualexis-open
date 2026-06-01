"""Oracle actions for governance bias measurement (scenario-level, not event_generator)."""

from __future__ import annotations

from dualexis.orchestration.models import SeverityLevel
from dualexis.simulation.scenario import SCENARIO_DEFINITIONS, ScenarioId

_ORACLE_BY_GT_LABEL: dict[str, str] = {
    "normal_operations": "monitor",
    "crowd_density_elevated": "notify_staff",
    "exit_blockage": "notify_staff",
    "acoustic_stress": "notify_staff",
    "multimodal_conflict": "request_review",
    "evacuation_review": "escalate",
}

_ESCALATION_ORACLE_ACTIONS = frozenset({"escalate", "request_review"})


def oracle_action_for_scenario(scenario_id: str) -> str:
    """Return the institutional oracle action for a built-in scenario."""
    definition = SCENARIO_DEFINITIONS[ScenarioId(scenario_id)]
    return _ORACLE_BY_GT_LABEL.get(
        definition.expected_ground_truth_label,
        "notify_staff",
    )


def actions_align(ai_action: str, oracle_action: str) -> bool:
    """Heuristic alignment between pipeline action strings and oracle labels."""
    ai = ai_action.lower().replace("-", "_")
    oracle = oracle_action.lower().replace("-", "_")
    if ai == oracle or ai in oracle or oracle in ai:
        return True
    pairs = (
        ("escalate", "escalate"),
        ("notify", "notify"),
        ("monitor", "monitor"),
        ("review", "review"),
        ("no_action", "monitor"),
    )
    return any(token in ai and token in oracle for token, _ in pairs)


def requires_escalation(oracle_action: str, severity: SeverityLevel) -> bool:
    """Whether the oracle expects escalation-level response."""
    if oracle_action in _ESCALATION_ORACLE_ACTIONS:
        return True
    return severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}


__all__ = [
    "actions_align",
    "oracle_action_for_scenario",
    "requires_escalation",
]
