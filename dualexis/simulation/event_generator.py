"""Synthetic semantic event generator for simulation.

Produces ``SemanticEvent`` records from world state. No raw media, biometrics,
or personal data are emitted.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent
from dualexis.simulation.scenario import ScenarioId
from dualexis.simulation.world import WorldState


def _severity_from_score(score: float) -> SeverityLevel:
    if score >= 0.85:
        return SeverityLevel.HIGH
    if score >= 0.65:
        return SeverityLevel.MEDIUM
    if score >= 0.4:
        return SeverityLevel.LOW
    return SeverityLevel.LOW


class SyntheticEventGenerator:
    """Generates domain ``SemanticEvent`` objects from anonymous world metrics."""

    def __init__(
        self,
        *,
        node_id: str = "sim-edge-001",
        start_time: datetime | None = None,
    ) -> None:
        self._node_id = node_id
        self._start_time = start_time or datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    def timestamp_for_tick(self, tick: int, *, tick_seconds: float) -> datetime:
        return self._start_time + timedelta(seconds=tick * tick_seconds)

    def generate_events(
        self,
        state: WorldState,
        *,
        scenario_id: ScenarioId,
        tick_seconds: float,
    ) -> tuple[SemanticEvent, ...]:
        """Emit zone-level semantic events for the current tick."""
        events: list[SemanticEvent] = []
        ts = self.timestamp_for_tick(state.tick, tick_seconds=tick_seconds)

        for zone_id, density in state.zone_density.items():
            activity = state.zone_activity.get(zone_id, 0.0)
            audio = state.zone_audio_stress.get(zone_id, 0.0)
            score = min(1.0, 0.35 * density + 0.35 * activity + 0.3 * audio)
            if score < 0.25 and scenario_id is not ScenarioId.NORMAL_FLOW:
                continue

            event_type, category, description = self._classify_signal(
                scenario_id=scenario_id,
                zone_id=zone_id,
                density=density,
                activity=activity,
                audio=audio,
            )
            if event_type is None:
                continue

            severity = _severity_from_score(score)
            events.append(
                SemanticEvent(
                    event_id=uuid5(
                        NAMESPACE_URL,
                        f"dualexis-sim:{self._node_id}:{scenario_id.value}:{state.tick}:{zone_id}",
                    ),
                    event_type=event_type,
                    source=EventSource.SIMULATOR,
                    zone_id=zone_id,
                    timestamp=ts,
                    confidence=round(score, 4),
                    severity=severity,
                    explanation=(
                        f"Simulated semantic event in zone '{zone_id}' for scenario "
                        f"'{scenario_id.value}': {description}"
                    ),
                    privacy_level=PrivacyLevel.SEMANTIC_ONLY,
                    metadata={
                        "category": category,
                        "sim_node_id": self._node_id,
                        "modalities": ",".join(self._modalities_for_scenario(scenario_id)),
                    },
                )
            )
        return tuple(events)

    @staticmethod
    def _modalities_for_scenario(scenario_id: ScenarioId) -> tuple[str, ...]:
        if scenario_id == ScenarioId.AUDIO_STRESS_SIGNAL:
            return ("audio",)
        if scenario_id == ScenarioId.MULTIMODAL_CONFLICT:
            return ("video", "audio")
        return ("video", "sensor")

    @staticmethod
    def _classify_signal(
        *,
        scenario_id: ScenarioId,
        zone_id: str,
        density: float,
        activity: float,
        audio: float,
    ) -> tuple[EventType | None, str, str]:
        if scenario_id == ScenarioId.NORMAL_FLOW:
            return (
                EventType.NORMAL_FLOW,
                "normal_flow",
                "Baseline anonymous flow within expected band",
            )
        if (
            scenario_id == ScenarioId.CROWD_ACCELERATION
            and zone_id == "cafeteria"
            and density > 0.45
        ):
            return (
                EventType.CROWD_ACCELERATION,
                "density_elevated",
                "Simulated crowd density surge (aggregate, zone-scoped)",
            )
        if scenario_id == ScenarioId.EXIT_BLOCKAGE and zone_id == "exit-lobby" and density > 0.5:
            return (
                EventType.EXIT_BLOCKAGE,
                "exit_blockage",
                "Simulated exit throughput reduction with upstream accumulation",
            )
        if (
            scenario_id == ScenarioId.AUDIO_STRESS_SIGNAL
            and zone_id == "hallway-a"
            and audio > 0.55
        ):
            return (
                EventType.AUDIO_STRESS_SIGNAL,
                "elevated_sound_level",
                "Synthetic acoustic stress indicator (no raw audio stored)",
            )
        if (
            scenario_id == ScenarioId.MULTIMODAL_CONFLICT
            and zone_id == "cafeteria"
            and activity < 0.3
            and audio > 0.6
        ):
            return (
                EventType.MULTIMODAL_CONFLICT,
                "conflicting_signals",
                "Video activity low while synthetic audio stress high",
            )
        if scenario_id == ScenarioId.EVACUATION_RECOMMENDATION and density > 0.6:
            return (
                EventType.EVACUATION_SIGNAL,
                "multi_zone_stress",
                "Elevated aggregate density contributing to evacuation review pattern",
            )
        if density > 0.7 or audio > 0.75:
            return (
                EventType.UNKNOWN,
                "elevated_activity",
                "Generic elevated zone activity (simulation)",
            )
        return (None, "", "")
