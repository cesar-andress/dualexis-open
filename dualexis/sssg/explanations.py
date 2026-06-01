"""State-transition explanations for operator-facing advisories."""

from __future__ import annotations

from dualexis.sssg.models import EvidenceRecord, SafetyState, StateTransition


def _state_phrase(state: SafetyState) -> str:
    return state.value.replace("_", " ").title()


def format_state_transition_explanation(
    transition: StateTransition,
    *,
    peer_zone_notes: tuple[str, ...] = (),
) -> str:
    """Build human-readable state-transition explanation (not event-only text)."""
    primary = transition.evidence[0].description if transition.evidence else "zone metrics"
    lines = [
        f"{primary} detected in {transition.zone_id}.",
    ]
    corroborations = [
        note for note in transition.corroboration_notes if note
    ] + list(peer_zone_notes)
    if corroborations:
        lines.append(f"Temporal corroboration: {'; '.join(corroborations)}.")
    lines.append(
        f"State changed from {_state_phrase(transition.from_state)} "
        f"to {_state_phrase(transition.to_state)}."
    )
    return " ".join(lines)


def corroboration_note_from_evidence(
    evidence: tuple[EvidenceRecord, ...],
    *,
    zone_id: str,
) -> tuple[str, ...]:
    """Summarise cross-metric corroboration within a zone."""
    notes: list[str] = []
    density = [e for e in evidence if e.kind.value == "zone_density" and e.zone_id == zone_id]
    audio = [e for e in evidence if e.kind.value == "zone_audio" and e.zone_id == zone_id]
    if density and audio:
        d_val = density[0].metric_value or 0.0
        if d_val >= 0.38:
            notes.append("crowd density escalation")
    exit_tp = [e for e in evidence if e.kind.value == "exit_throughput"]
    if exit_tp and (exit_tp[0].metric_value or 1.0) < 0.55:
        notes.append("exit throughput reduction")
    return tuple(notes)


__all__ = [
    "corroboration_note_from_evidence",
    "format_state_transition_explanation",
]
