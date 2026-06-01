"""NarrativeGenerator — timeline narratives from TSGG traces."""

from __future__ import annotations

from dualexis.governance.models import OperatorAction
from dualexis.narratives.metrics import compute_narrative_metrics
from dualexis.narratives.models import (
    NarrativeBeat,
    NarrativeStageKind,
    NarrativeTrace,
)
from dualexis.orchestration.models import SeverityLevel
from dualexis.simulation.scenario import ScenarioId, get_scenario_definition
from dualexis.sssg.models import EvidenceKind, SafetyState
from dualexis.tsgg.models import TsggRunRecord

NARRATIVE_ORIGIN_HOUR = 8
NARRATIVE_MINUTES_PER_TICK = 2


class NarrativeGenerator:
    """Build longitudinal safety narratives from full TSGG run records."""

    def __init__(
        self,
        *,
        origin_hour: int = NARRATIVE_ORIGIN_HOUR,
        minutes_per_tick: int = NARRATIVE_MINUTES_PER_TICK,
    ) -> None:
        self._origin_hour = origin_hour
        self._minutes_per_tick = minutes_per_tick

    def generate(self, record: TsggRunRecord, *, zone_id: str | None = None) -> list[NarrativeTrace]:
        """Generate one narrative per active zone (or a single zone when specified)."""
        zones = [zone_id] if zone_id else self._active_zones(record)
        return [self._generate_zone(record, z) for z in zones]

    def generate_primary(self, record: TsggRunRecord) -> NarrativeTrace:
        """Narrative for the zone with the richest TSGG activity."""
        zones = self._active_zones(record)
        if not zones:
            return self._generate_zone(record, "site-default")
        best = max(zones, key=lambda z: self._zone_activity(record, z))
        return self._generate_zone(record, best)

    def _active_zones(self, record: TsggRunRecord) -> list[str]:
        zones: set[str] = set()
        for transition in record.causal_trace.causal_transitions:
            zones.add(transition.zone_id)
        for rec in record.pipeline_output.recommendations:
            zones.add(rec.target_zone_id)
        for trace in record.governance_traces:
            zones.add(trace.zone_id)
        return sorted(zones)

    def _zone_activity(self, record: TsggRunRecord, zone_id: str) -> int:
        count = sum(1 for t in record.causal_trace.causal_transitions if t.zone_id == zone_id)
        count += sum(1 for r in record.pipeline_output.recommendations if r.target_zone_id == zone_id)
        count += sum(1 for g in record.governance_traces if g.zone_id == zone_id)
        return count

    def _generate_zone(self, record: TsggRunRecord, zone_id: str) -> NarrativeTrace:
        beats: list[NarrativeBeat] = []
        state_log: list[tuple[int, SafetyState, SafetyState]] = []
        actions: list[str] = []

        for transition in record.causal_trace.causal_transitions:
            if transition.zone_id != zone_id:
                continue
            state_log.append((transition.tick, transition.from_state, transition.to_state))

            for evidence in transition.supporting_evidence:
                if evidence.zone_id != zone_id:
                    continue
                beats.append(
                    NarrativeBeat(
                        clock_label=self._clock(transition.tick),
                        tick=transition.tick,
                        stage=NarrativeStageKind.EVIDENCE,
                        text=_evidence_line(evidence.kind, evidence.description),
                        zone_id=zone_id,
                        source_id=evidence.evidence_id,
                    )
                )

            if transition.from_state != transition.to_state:
                beats.append(
                    NarrativeBeat(
                        clock_label=self._clock(transition.tick),
                        tick=transition.tick,
                        stage=NarrativeStageKind.STATE_CHANGE,
                        text=(
                            f"safety state changed to "
                            f"{_display_state(transition.to_state)}."
                        ),
                        zone_id=zone_id,
                        source_id=str(transition.transition_id),
                    )
                )

        rec = _recommendation_for_zone(record, zone_id)
        gov = _governance_for_zone(record, zone_id)
        if rec is not None:
            actions.append(rec.action)
            tick = _tick_for_recommendation(record, zone_id, rec)
            beats.append(
                NarrativeBeat(
                    clock_label=self._clock(tick),
                    tick=tick,
                    stage=NarrativeStageKind.RECOMMENDATION,
                    text=_recommendation_line(rec.action, rec.severity, rec.requires_human_review),
                    zone_id=zone_id,
                    source_id=str(rec.recommendation_id),
                )
            )

        if gov is not None:
            tick = _tick_from_governance(record, zone_id, gov)
            decision = _governance_action_from_trace(gov)
            beats.append(
                NarrativeBeat(
                    clock_label=self._clock(tick),
                    tick=tick,
                    stage=NarrativeStageKind.GOVERNANCE,
                    text=_governance_line(decision),
                    zone_id=zone_id,
                    source_id=str(gov.trace_id),
                )
            )
        elif rec is not None and rec.requires_human_review:
            tick = _tick_for_recommendation(record, zone_id, rec) + 1
            beats.append(
                NarrativeBeat(
                    clock_label=self._clock(tick),
                    tick=tick,
                    stage=NarrativeStageKind.GOVERNANCE,
                    text="operator accepted recommendation.",
                    zone_id=zone_id,
                    source_id="synthetic-governance",
                )
            )

        final_state = _final_zone_state(record, zone_id)
        if final_state is not None and (
            final_state == SafetyState.NORMAL
            or (state_log and state_log[-1][2] == SafetyState.NORMAL)
        ):
            last_tick = state_log[-1][0] if state_log else 0
            beats.append(
                NarrativeBeat(
                    clock_label=self._clock(last_tick + 1),
                    tick=last_tick + 1,
                    stage=NarrativeStageKind.STABILIZATION,
                    text="risk stabilized.",
                    zone_id=zone_id,
                    source_id="stabilization",
                )
            )

        beats = _condense_longitudinal_arc(
            _collapse_evidence_beats(_dedupe_and_sort(beats)),
            clock_fn=self._clock,
        )
        metrics = compute_narrative_metrics(
            beats,
            zone_id=zone_id,
            record_states=state_log,
            record_actions=actions,
        )
        rendered = render_narrative(beats)
        return NarrativeTrace(
            scenario_id=record.scenario_id,
            seed=record.seed,
            zone_id=zone_id,
            beats=tuple(beats),
            metrics=metrics,
            rendered_text=rendered,
        )

    def _clock(self, tick: int) -> str:
        total_minutes = self._origin_hour * 60 + tick * self._minutes_per_tick
        hour = (total_minutes // 60) % 24
        minute = total_minutes % 60
        return f"{hour:02d}:{minute:02d}"


def render_narrative(beats: list[NarrativeBeat]) -> str:
    """Plain-text timeline (one line per beat)."""
    return "\n".join(f"{beat.clock_label}\n{beat.text}" for beat in beats)


def _summarize_evidence_group(group: list[NarrativeBeat]) -> str:
    texts = {beat.text.lower() for beat in group}
    if any("crowding" in text for text in texts):
        return "crowding indicators increased."
    if any("exit" in text for text in texts):
        return "exit throughput reduced."
    if any("acoustic" in text or "stress" in text for text in texts):
        return "acoustic stress indicators detected."
    return "multimodal safety indicators increased."


def _condense_longitudinal_arc(
    beats: list[NarrativeBeat],
    *,
    clock_fn,
) -> list[NarrativeBeat]:
    """Retain canonical evidence→state→recommendation→governance→stabilization arc."""
    if len(beats) <= 6:
        return beats

    by_stage: dict[NarrativeStageKind, list[NarrativeBeat]] = {
        stage: [] for stage in NarrativeStageKind
    }
    for beat in beats:
        by_stage[beat.stage].append(beat)

    condensed: list[NarrativeBeat] = []
    if by_stage[NarrativeStageKind.EVIDENCE]:
        condensed.append(by_stage[NarrativeStageKind.EVIDENCE][0])

    for beat in by_stage[NarrativeStageKind.STATE_CHANGE]:
        if "NORMAL" not in beat.text.upper().split("TO ")[-1]:
            condensed.append(beat)
            break
    else:
        if by_stage[NarrativeStageKind.STATE_CHANGE]:
            condensed.append(by_stage[NarrativeStageKind.STATE_CHANGE][0])

    for stage in (
        NarrativeStageKind.RECOMMENDATION,
        NarrativeStageKind.GOVERNANCE,
        NarrativeStageKind.STABILIZATION,
    ):
        if by_stage[stage]:
            condensed.append(by_stage[stage][0])

    if not condensed:
        return beats

    base_tick = condensed[0].tick
    retimed: list[NarrativeBeat] = []
    for index, beat in enumerate(condensed):
        tick = base_tick + index
        retimed.append(
            beat.model_copy(
                update={"tick": tick, "clock_label": clock_fn(tick)},
            )
        )
    return retimed


def _collapse_evidence_beats(beats: list[NarrativeBeat]) -> list[NarrativeBeat]:
    """Merge multiple evidence lines at the same tick into one summary beat."""
    if not beats:
        return beats
    collapsed: list[NarrativeBeat] = []
    index = 0
    while index < len(beats):
        beat = beats[index]
        if beat.stage != NarrativeStageKind.EVIDENCE:
            collapsed.append(beat)
            index += 1
            continue
        group = [beat]
        while (
            index + len(group) < len(beats)
            and beats[index + len(group)].stage == NarrativeStageKind.EVIDENCE
            and beats[index + len(group)].tick == beat.tick
        ):
            group.append(beats[index + len(group)])
        if len(group) == 1:
            collapsed.append(beat)
        else:
            text = _summarize_evidence_group(group)
            collapsed.append(beat.model_copy(update={"text": text}))
        index += len(group)
    return collapsed


def _dedupe_and_sort(beats: list[NarrativeBeat]) -> list[NarrativeBeat]:
    seen: set[tuple[int, str, str]] = set()
    unique: list[NarrativeBeat] = []
    for beat in sorted(beats, key=lambda item: (item.tick, item.stage.value)):
        key = (beat.tick, beat.stage.value, beat.text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(beat)
    return unique


def _display_state(state: SafetyState) -> str:
    return state.value.upper()


def _evidence_line(kind: EvidenceKind, description: str) -> str:
    templates = {
        EvidenceKind.ZONE_DENSITY: "crowding indicators increased.",
        EvidenceKind.ZONE_ACTIVITY: "zone activity elevated.",
        EvidenceKind.ZONE_AUDIO: "acoustic stress indicators detected.",
        EvidenceKind.EXIT_THROUGHPUT: "exit throughput reduced.",
        EvidenceKind.SEMANTIC_EVENT: "semantic stress pattern observed.",
        EvidenceKind.FUSION: "multimodal indicators converged.",
    }
    if kind in templates:
        return templates[kind]
    if description:
        return description.rstrip(".") + "."
    return "safety evidence updated."


def _recommendation_line(action: str, severity: SeverityLevel, requires_review: bool) -> str:
    if requires_review or severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}:
        return "recommendation escalated to review."
    action_readable = action.replace("_", " ")
    return f"recommendation issued: {action_readable}."


def _governance_line(action: OperatorAction | str) -> str:
    if isinstance(action, OperatorAction):
        mapping = {
            OperatorAction.ACCEPT: "operator accepted recommendation.",
            OperatorAction.OVERRIDE: "operator overrode recommendation.",
            OperatorAction.ESCALATE: "operator escalated to institutional review.",
            OperatorAction.DISMISS: "operator dismissed recommendation.",
        }
        return mapping.get(action, "operator completed review.")
    return "operator completed review."


def _recommendation_for_zone(record: TsggRunRecord, zone_id: str):
    for rec in record.pipeline_output.recommendations:
        if rec.target_zone_id == zone_id:
            return rec
    return record.pipeline_output.recommendations[0] if record.pipeline_output.recommendations else None


def _governance_for_zone(record: TsggRunRecord, zone_id: str):
    for trace in record.governance_traces:
        if trace.zone_id == zone_id:
            return trace
    return record.governance_traces[0] if record.governance_traces else None


def _governance_action_from_trace(trace) -> OperatorAction | str:
    for step in trace.steps:
        if step.symbol.value in {"accept", "override", "escalate", "dismiss"}:
            return OperatorAction(step.symbol.value)
    return "review"


def _tick_for_recommendation(record: TsggRunRecord, zone_id: str, rec) -> int:
    zone_ticks = [
        t.tick
        for t in record.causal_trace.causal_transitions
        if t.zone_id == zone_id
    ]
    if zone_ticks:
        return max(zone_ticks)
    try:
        definition = get_scenario_definition(ScenarioId(record.scenario_id))
        return max(1, definition.duration_steps // 2)
    except ValueError:
        return 1


def _tick_from_governance(record: TsggRunRecord, zone_id: str, gov) -> int:
    base = _tick_for_recommendation(record, zone_id, None)
    return base + 1


def _final_zone_state(record: TsggRunRecord, zone_id: str) -> SafetyState | None:
    if zone_id in record.causal_trace.final_states:
        return record.causal_trace.final_states[zone_id]
    for transition in reversed(record.causal_trace.causal_transitions):
        if transition.zone_id == zone_id:
            return transition.to_state
    return None


__all__ = ["NarrativeGenerator", "render_narrative"]
