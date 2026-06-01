"""Semantic signatures per seed for robustness comparison."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from dualexis.pipeline import run_pipeline
from dualexis.pipeline.config import PipelineRunConfig
from dualexis.simulation.runner import run_scenario
from dualexis.sssg.runner import build_sssg_trace_from_scenario

ROBUSTNESS_PIPELINE_CONFIG = PipelineRunConfig(
    enable_privacy_runtime=True,
    enable_temporal_graph=True,
    enable_explanation_layer=True,
    enable_sssg=True,
)


def _hash_text(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


@dataclass(frozen=True, slots=True)
class SeedSignatures:
    event: frozenset[str]
    state: frozenset[str]
    recommendation: frozenset[str]
    explanation: frozenset[str]


def collect_signatures(scenario: str, seed: int) -> SeedSignatures:
    """Collect all stability signatures for one (scenario, seed) run."""
    simulation = run_scenario(scenario, seed=seed)
    trace = build_sssg_trace_from_scenario(scenario, seed=seed)
    output = run_pipeline(
        scenario,
        seed=seed,
        run_config=ROBUSTNESS_PIPELINE_CONFIG,
    )

    event_parts: set[str] = set()
    for event in simulation.events:
        category = event.metadata.get("category", event.event_type.value)
        tick = event.metadata.get("tick", "0")
        event_parts.add(f"{event.zone_id}:{category}:{tick}")

    state_parts = {
        f"{t.zone_id}:{t.from_state.value}->{t.to_state.value}:{t.tick}"
        for t in trace.transitions
    }
    for zone_id, state in trace.final_states.items():
        state_parts.add(f"{zone_id}:final:{state.value}")

    recommendation_parts: set[str] = set()
    for rec in output.recommendations:
        recommendation_parts.add(f"{rec.target_zone_id}:{rec.action}:{rec.severity.value}")
    if not recommendation_parts:
        for zone_id, state in trace.final_states.items():
            if state.value != "normal":
                recommendation_parts.add(f"{zone_id}:synthetic:{state.value}")

    explanation_parts: set[str] = set()
    for transition in trace.transitions:
        digest = _hash_text(transition.explanation)
        explanation_parts.add(f"{transition.zone_id}:{transition.tick}:{digest}")
    for rec in output.recommendations:
        digest = _hash_text(rec.rationale)
        explanation_parts.add(f"{rec.target_zone_id}:rec:{digest}")
    for event in output.normalized_events:
        if event.explanation:
            digest = _hash_text(event.explanation)
            explanation_parts.add(f"{event.zone_id}:evt:{digest}")

    return SeedSignatures(
        event=frozenset(event_parts),
        state=frozenset(state_parts),
        recommendation=frozenset(recommendation_parts),
        explanation=frozenset(explanation_parts),
    )


__all__ = ["ROBUSTNESS_PIPELINE_CONFIG", "SeedSignatures", "collect_signatures"]
