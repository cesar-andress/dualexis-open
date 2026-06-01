"""Safety-state transition rules and allowed state machine edges."""

from __future__ import annotations

from dualexis.sssg.models import SafetyState

# Declared transition rules (from_state -> to_state).
ALLOWED_TRANSITIONS: frozenset[tuple[SafetyState, SafetyState]] = frozenset(
    {
        (SafetyState.NORMAL, SafetyState.CROWDING_RISK),
        (SafetyState.NORMAL, SafetyState.EXIT_IMPAIRMENT),
        (SafetyState.NORMAL, SafetyState.AUDIO_STRESS),
        (SafetyState.NORMAL, SafetyState.MULTI_MODAL_CONFLICT),
        (SafetyState.NORMAL, SafetyState.EVACUATION_CANDIDATE),
        (SafetyState.CROWDING_RISK, SafetyState.EVACUATION_CANDIDATE),
        (SafetyState.CROWDING_RISK, SafetyState.NORMAL),
        (SafetyState.EXIT_IMPAIRMENT, SafetyState.EVACUATION_CANDIDATE),
        (SafetyState.EXIT_IMPAIRMENT, SafetyState.NORMAL),
        (SafetyState.AUDIO_STRESS, SafetyState.NORMAL),
        (SafetyState.MULTI_MODAL_CONFLICT, SafetyState.NORMAL),
        (SafetyState.MULTI_MODAL_CONFLICT, SafetyState.EVACUATION_CANDIDATE),
        (SafetyState.EVACUATION_CANDIDATE, SafetyState.NORMAL),
        (SafetyState.EVACUATION_CANDIDATE, SafetyState.CROWDING_RISK),
        # Lateral escalations
        (SafetyState.CROWDING_RISK, SafetyState.EXIT_IMPAIRMENT),
        (SafetyState.AUDIO_STRESS, SafetyState.MULTI_MODAL_CONFLICT),
    }
)

# Highlighted causal chains referenced in the manuscript.
DOCUMENTED_TRANSITION_CHAINS: tuple[tuple[SafetyState, SafetyState], ...] = (
    (SafetyState.NORMAL, SafetyState.CROWDING_RISK),
    (SafetyState.CROWDING_RISK, SafetyState.EVACUATION_CANDIDATE),
    (SafetyState.EXIT_IMPAIRMENT, SafetyState.EVACUATION_CANDIDATE),
)


def is_allowed_transition(from_state: SafetyState, to_state: SafetyState) -> bool:
    if from_state == to_state:
        return True
    return (from_state, to_state) in ALLOWED_TRANSITIONS


def resolve_transition(
    current: SafetyState,
    proposed: SafetyState,
) -> SafetyState:
    """Apply transition rules; reject disallowed jumps by staying in current state."""
    if current == proposed:
        return current
    if is_allowed_transition(current, proposed):
        return proposed
    # Escalation fallback: step through documented chain if possible
    for from_state, to_state in DOCUMENTED_TRANSITION_CHAINS:
        if current == from_state and proposed == to_state:
            return to_state
    if proposed == SafetyState.EVACUATION_CANDIDATE and current in {
        SafetyState.CROWDING_RISK,
        SafetyState.EXIT_IMPAIRMENT,
    }:
        return SafetyState.EVACUATION_CANDIDATE
    return current


__all__ = [
    "ALLOWED_TRANSITIONS",
    "DOCUMENTED_TRANSITION_CHAINS",
    "is_allowed_transition",
    "resolve_transition",
]
