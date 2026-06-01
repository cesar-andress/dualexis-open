"""Map world metrics and semantic events to SSSG evidence records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from dualexis.semantic_events.models import EventType, SemanticEvent
from dualexis.simulation.scenario import ScenarioId
from dualexis.simulation.world import WorldState
from dualexis.sssg.models import EvidenceKind, EvidenceRecord, SafetyState


def _label_for_event_type(event_type: EventType) -> str:
    mapping = {
        EventType.NORMAL_FLOW: "normal flow band",
        EventType.CROWD_ACCELERATION: "crowd density elevation",
        EventType.EXIT_BLOCKAGE: "exit throughput reduction",
        EventType.AUDIO_STRESS_SIGNAL: "elevated acoustic stress",
        EventType.MULTIMODAL_CONFLICT: "conflicting multimodal signals",
        EventType.EVACUATION_SIGNAL: "multi-zone stress pattern",
    }
    return mapping.get(event_type, event_type.value.replace("_", " "))


def evidence_from_world_state(
    state: WorldState,
    *,
    zone_id: str,
    timestamp: datetime,
    evidence_index: int = 0,
) -> tuple[EvidenceRecord, ...]:
    """Derive metric evidence for one zone from anonymous world state."""
    records: list[EvidenceRecord] = []
    density = state.zone_density.get(zone_id, 0.0)
    activity = state.zone_activity.get(zone_id, 0.0)
    audio = state.zone_audio_stress.get(zone_id, 0.0)

    if density > 0.0:
        records.append(
            EvidenceRecord(
                evidence_id=f"ev-{zone_id}-density-{state.tick}",
                kind=EvidenceKind.ZONE_DENSITY,
                zone_id=zone_id,
                tick=state.tick,
                timestamp=timestamp,
                metric_value=density,
                description=f"Zone density {density:.2f}",
            )
        )
    if activity > 0.0:
        records.append(
            EvidenceRecord(
                evidence_id=f"ev-{zone_id}-activity-{state.tick}",
                kind=EvidenceKind.ZONE_ACTIVITY,
                zone_id=zone_id,
                tick=state.tick,
                timestamp=timestamp,
                metric_value=activity,
                description=f"Zone activity {activity:.2f}",
            )
        )
    if audio > 0.0:
        records.append(
            EvidenceRecord(
                evidence_id=f"ev-{zone_id}-audio-{state.tick}",
                kind=EvidenceKind.ZONE_AUDIO,
                zone_id=zone_id,
                tick=state.tick,
                timestamp=timestamp,
                metric_value=audio,
                description=f"Zone audio stress {audio:.2f}",
            )
        )

    for exit_id, throughput in state.exit_throughput.items():
        records.append(
            EvidenceRecord(
                evidence_id=f"ev-exit-{exit_id}-{state.tick}",
                kind=EvidenceKind.EXIT_THROUGHPUT,
                zone_id=zone_id,
                tick=state.tick,
                timestamp=timestamp,
                metric_value=throughput,
                description=f"Exit {exit_id} throughput {throughput:.2f}",
            )
        )

    if not records and evidence_index == 0:
        records.append(
            EvidenceRecord(
                evidence_id=f"ev-{zone_id}-baseline-{state.tick}",
                kind=EvidenceKind.ZONE_ACTIVITY,
                zone_id=zone_id,
                tick=state.tick,
                timestamp=timestamp,
                metric_value=0.0,
                description="Baseline zone observation",
            )
        )
    return tuple(records)


def evidence_from_semantic_event(event: SemanticEvent) -> EvidenceRecord:
    """Wrap a published semantic event as structured evidence."""
    category = event.metadata.get("category", event.event_type.value)
    return EvidenceRecord(
        evidence_id=f"ev-event-{event.event_id}",
        kind=EvidenceKind.SEMANTIC_EVENT,
        zone_id=event.zone_id,
        tick=int(event.metadata.get("tick", "0") or "0"),
        timestamp=event.timestamp,
        metric_value=event.confidence,
        description=f"{_label_for_event_type(event.event_type)} ({category})",
        source_event_id=event.event_id,
    )


def infer_safety_state_from_evidence(
    evidence: tuple[EvidenceRecord, ...],
    *,
    scenario_id: ScenarioId | None = None,
    zone_id: str,
) -> SafetyState:
    """Map evidence bundle to a candidate safety state (rule-based)."""
    max_density = 0.0
    max_audio = 0.0
    min_activity = 1.0
    min_throughput = 1.0
    has_conflict_event = False
    has_evacuation_event = False
    has_exit_block = False

    for record in evidence:
        if record.zone_id != zone_id and record.kind != EvidenceKind.EXIT_THROUGHPUT:
            continue
        if record.kind == EvidenceKind.ZONE_DENSITY and record.metric_value is not None:
            max_density = max(max_density, record.metric_value)
        if record.kind == EvidenceKind.ZONE_AUDIO and record.metric_value is not None:
            max_audio = max(max_audio, record.metric_value)
        if record.kind == EvidenceKind.ZONE_ACTIVITY and record.metric_value is not None:
            min_activity = min(min_activity, record.metric_value)
        if record.kind == EvidenceKind.EXIT_THROUGHPUT and record.metric_value is not None:
            min_throughput = min(min_throughput, record.metric_value)
        if record.kind == EvidenceKind.SEMANTIC_EVENT:
            desc = record.description.lower()
            if "conflict" in desc:
                has_conflict_event = True
            if "evacuation" in desc or "multi-zone stress" in desc:
                has_evacuation_event = True
            if "exit" in desc and "block" in desc:
                has_exit_block = True

    if scenario_id == ScenarioId.EVACUATION_RECOMMENDATION or has_evacuation_event:
        if max_density >= 0.52:
            return SafetyState.EVACUATION_CANDIDATE
    if has_conflict_event or (
        scenario_id == ScenarioId.MULTIMODAL_CONFLICT
        and max_audio >= 0.52
        and min_activity < 0.28
    ):
        return SafetyState.MULTI_MODAL_CONFLICT
    if has_exit_block or min_throughput < 0.55 or (
        scenario_id == ScenarioId.EXIT_BLOCKAGE and max_density >= 0.42
    ):
        return SafetyState.EXIT_IMPAIRMENT
    if scenario_id == ScenarioId.AUDIO_STRESS_SIGNAL and max_audio >= 0.55:
        return SafetyState.AUDIO_STRESS
    if max_density >= 0.38 or scenario_id == ScenarioId.CROWD_ACCELERATION:
        if max_density >= 0.38:
            return SafetyState.CROWDING_RISK
    if scenario_id == ScenarioId.NORMAL_FLOW:
        return SafetyState.NORMAL
    if max_density < 0.35 and max_audio < 0.45:
        return SafetyState.NORMAL
    if max_density >= 0.38:
        return SafetyState.CROWDING_RISK
    return SafetyState.NORMAL


def semantic_label_to_safety_state(semantic_label: str) -> SafetyState:
    """Map independent GT semantic labels to safety states."""
    mapping = {
        "normal_flow": SafetyState.NORMAL,
        "crowd_density_elevated": SafetyState.CROWDING_RISK,
        "exit_blockage": SafetyState.EXIT_IMPAIRMENT,
        "exit_throughput_reduced": SafetyState.EXIT_IMPAIRMENT,
        "acoustic_stress": SafetyState.AUDIO_STRESS,
        "multimodal_conflict": SafetyState.MULTI_MODAL_CONFLICT,
        "evacuation_stress_pattern": SafetyState.EVACUATION_CANDIDATE,
    }
    return mapping.get(semantic_label, SafetyState.NORMAL)


__all__ = [
    "evidence_from_semantic_event",
    "evidence_from_world_state",
    "infer_safety_state_from_evidence",
    "semantic_label_to_safety_state",
]
