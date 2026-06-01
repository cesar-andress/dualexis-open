"""Causal path extraction for CSSG."""

from __future__ import annotations

from dualexis.sssg.models import SafetyState
from dualexis.cssg.models import CausalFactor, CausalStateTransitionTrace


def find_root_causes(
    trace: CausalStateTransitionTrace,
    zone_id: str,
    tick: int,
) -> tuple[CausalFactor, ...]:
    """
    Walk backward along zone transitions up to ``tick`` and return root causal factors.

    Roots are primary ``contributes_to`` / ``triggers`` factors at the earliest
  explaining transition in the chain (typically emerging from NORMAL).
    """
    zone_steps = [
        t
        for t in trace.causal_transitions
        if t.zone_id == zone_id and t.tick <= tick
    ]
    zone_steps.sort(key=lambda item: item.tick)
    if not zone_steps:
        return ()

    roots: list[CausalFactor] = []
    seen: set[str] = set()

    for step in zone_steps:
        primary = [
            f
            for f in step.causal_factors
            if f.edge_type.value in {"contributes_to", "triggers"}
        ]
        for factor in primary:
            if factor.factor_id not in seen:
                roots.append(factor)
                seen.add(factor.factor_id)
        if step.from_state == SafetyState.NORMAL:
            break

    if not roots and zone_steps:
        roots = list(zone_steps[0].causal_factors[:2])
    return tuple(roots)


def causal_path_to_tick(
    trace: CausalStateTransitionTrace,
    zone_id: str,
    tick: int,
) -> tuple[tuple[SafetyState, SafetyState], ...]:
    """Return ordered (from, to) state pairs along the zone timeline up to tick."""
    zone_steps = [
        t
        for t in trace.causal_transitions
        if t.zone_id == zone_id and t.tick <= tick
    ]
    zone_steps.sort(key=lambda item: item.tick)
    return tuple((t.from_state, t.to_state) for t in zone_steps)


def causal_path_depth(
    trace: CausalStateTransitionTrace,
    zone_id: str,
    tick: int,
) -> int:
    """Number of causal transitions on the path (explanation depth)."""
    return len(causal_path_to_tick(trace, zone_id, tick))


__all__ = [
    "causal_path_depth",
    "causal_path_to_tick",
    "find_root_causes",
]
