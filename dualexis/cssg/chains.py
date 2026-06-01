"""Human-readable causal explanation chains for CSSG."""

from __future__ import annotations

from dualexis.sssg.models import SafetyState
from dualexis.cssg.models import CausalStateTransition, CausalStateTransitionTrace


def _state_label(state: SafetyState) -> str:
    return state.value.replace("_", " ").upper()


def format_transition_rationale(transition: CausalStateTransition) -> str:
    """One-step rationale from causal factors."""
    drivers = ", ".join(
        f"{f.edge_type.value} ({f.description})" for f in transition.causal_factors[:2]
    )
    conf = f"{transition.confidence:.0%} confidence"
    return f"{drivers}; {conf}"


def build_explanation_chain(
    trace: CausalStateTransitionTrace,
    zone_id: str,
    *,
    terminal_state: SafetyState | None = None,
) -> str:
    """
    Build a multi-line causal chain, e.g.::

        NORMAL -> CROWDING_RISK -> EXIT_IMPAIRMENT -> EVACUATION_CANDIDATE
    """
    steps = [t for t in trace.causal_transitions if t.zone_id == zone_id]
    steps.sort(key=lambda item: item.tick)
    if terminal_state is not None:
        filtered: list[CausalStateTransition] = []
        for step in steps:
            filtered.append(step)
            if step.to_state == terminal_state:
                break
        steps = filtered

    if not steps:
        return f"{_state_label(SafetyState.NORMAL)}"

    chain_states: list[SafetyState] = [steps[0].from_state]
    rationales: list[str] = []
    for step in steps:
        chain_states.append(step.to_state)
        rationales.append(format_transition_rationale(step))

    lines: list[str] = []
    for index, state in enumerate(chain_states):
        indent = "   " * index
        arrow = " ->" if index < len(chain_states) - 1 else ""
        lines.append(f"{indent}{_state_label(state)}{arrow}")
        if index < len(rationales):
            lines.append(f"{indent}   ({rationales[index]})")
    return "\n".join(lines)


def canonical_escalation_chain_text() -> str:
    """Reference chain for manuscript examples."""
    return build_explanation_chain_from_states(
        [
            (SafetyState.NORMAL, SafetyState.CROWDING_RISK, "rising zone density"),
            (SafetyState.CROWDING_RISK, SafetyState.EXIT_IMPAIRMENT, "exit throughput reduction"),
            (
                SafetyState.EXIT_IMPAIRMENT,
                SafetyState.EVACUATION_CANDIDATE,
                "compound stress triggers evacuation review",
            ),
        ]
    )


def build_explanation_chain_from_states(
    steps: list[tuple[SafetyState, SafetyState, str]],
) -> str:
    if not steps:
        return _state_label(SafetyState.NORMAL)
    lines: list[str] = [_state_label(steps[0][0])]
    for index, (from_state, to_state, rationale) in enumerate(steps):
        indent = "   " * (index + 1)
        lines.append(f"{indent}-> {_state_label(to_state)}")
        lines.append(f"{indent}   ({rationale})")
        if index == 0:
            lines[0] = f"{_state_label(from_state)}"
    return "\n".join(lines)


__all__ = [
    "build_explanation_chain",
    "build_explanation_chain_from_states",
    "canonical_escalation_chain_text",
    "format_transition_rationale",
]
