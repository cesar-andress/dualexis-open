"""Metric-heuristic semantic event emission from decoupled emission profiles.

Consumes ``experiments/simulator/emission_profiles/`` only. Does not import
``gt_rules`` or ground-truth rule YAML.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent
from dualexis.simulation.emission_profiles import (
    EmissionRule,
    load_emission_profile,
    emission_rule_matches_tick,
)
from dualexis.simulation.scenario import ScenarioId
from dualexis.simulation.world import WorldState


def _severity_from_metrics(density: float, activity: float, audio: float) -> SeverityLevel:
    score = min(1.0, 0.4 * density + 0.35 * activity + 0.25 * audio)
    if score >= 0.82:
        return SeverityLevel.HIGH
    if score >= 0.62:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def _description_for_label(semantic_label: str, zone_id: str, scenario_id: ScenarioId) -> str:
    return (
        f"Heuristic semantic event '{semantic_label}' in zone '{zone_id}' "
        f"for scenario '{scenario_id.value}' (decoupled emission profile)"
    )


def _modalities_for_scenario(scenario_id: ScenarioId) -> tuple[str, ...]:
    if scenario_id == ScenarioId.AUDIO_STRESS_SIGNAL:
        return ("audio",)
    if scenario_id == ScenarioId.MULTIMODAL_CONFLICT:
        return ("video", "audio")
    return ("video", "sensor")


def _rng_for_decision(
    *,
    seed: int,
    scenario_id: ScenarioId,
    tick: int,
    zone_id: str,
    semantic_label: str,
    salt: str,
) -> random.Random:
    token = f"{seed}:{scenario_id.value}:{tick}:{zone_id}:{semantic_label}:{salt}"
    subseed = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(subseed)


def _should_emit(rule: EmissionRule, *, seed: int, scenario_id: ScenarioId, tick: int, zone_id: str) -> bool:
    if rule.miss_probability <= 0.0:
        return True
    rng = _rng_for_decision(
        seed=seed,
        scenario_id=scenario_id,
        tick=tick,
        zone_id=zone_id,
        semantic_label=rule.semantic_label,
        salt="miss",
    )
    return rng.random() >= rule.miss_probability


def emit_metric_heuristic_events(
    state: WorldState,
    *,
    scenario_id: ScenarioId,
    seed: int,
    tick_seconds: float,
    node_id: str,
    start_time: datetime,
) -> tuple[SemanticEvent, ...]:
    """Emit simulator semantic events for one tick using decoupled emission profiles."""
    profile = load_emission_profile(scenario_id)
    ts = start_time + timedelta(seconds=state.tick * tick_seconds)
    events: list[SemanticEvent] = []
    seen: set[tuple[int, str, str]] = set()

    for rule in profile.emit_rules:
        zone_ids = emission_rule_matches_tick(
            rule,
            tick=state.tick,
            zone_density=state.zone_density,
            zone_activity=state.zone_activity,
            zone_audio=state.zone_audio_stress,
            exit_throughput=state.exit_throughput,
        )
        for zone_id in zone_ids:
            if not _should_emit(rule, seed=seed, scenario_id=scenario_id, tick=state.tick, zone_id=zone_id):
                continue
            key = (state.tick, zone_id, rule.semantic_label)
            if key in seen:
                continue
            seen.add(key)

            density = state.zone_density.get(zone_id, 0.0)
            activity = state.zone_activity.get(zone_id, 0.0)
            audio = state.zone_audio_stress.get(zone_id, 0.0)
            score = min(1.0, 0.35 * density + 0.35 * activity + 0.3 * audio)

            events.append(
                SemanticEvent(
                    event_id=uuid5(
                        NAMESPACE_URL,
                        (
                            f"dualexis-sim:{node_id}:{scenario_id.value}:"
                            f"{seed}:{state.tick}:{zone_id}:{rule.semantic_label}"
                        ),
                    ),
                    event_type=rule.expected_event_type,
                    source=EventSource.SIMULATOR,
                    zone_id=zone_id,
                    timestamp=ts,
                    confidence=round(score, 4),
                    severity=_severity_from_metrics(density, activity, audio),
                    explanation=_description_for_label(rule.semantic_label, zone_id, scenario_id),
                    privacy_level=PrivacyLevel.SEMANTIC_ONLY,
                    metadata={
                        "category": rule.semantic_label,
                        "sim_node_id": node_id,
                        "modalities": ",".join(_modalities_for_scenario(scenario_id)),
                        "tick": str(state.tick),
                        "emission_profile_version": profile.version,
                    },
                )
            )

    return tuple(events)


__all__ = ["emit_metric_heuristic_events"]
