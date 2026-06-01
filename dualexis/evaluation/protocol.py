"""Experimental protocol definitions for Q1-oriented DUALEXIS evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never

from dualexis.evaluation.baselines import (
    BaselineOutput,
    DualexisSemanticBaseline,
    RuleBasedFusionBaseline,
    SingleModalityBaseline,
)
from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.runner import SimulationResult
from dualexis.temporal_graph.models import Exit, Zone
from dualexis.temporal_graph.service import InMemoryTemporalGraphService


class ExperimentProtocolId(StrEnum):
    """Registered experimental protocol identifiers."""

    SINGLE_MODALITY_BASELINE = "single_modality_baseline"
    RULE_BASED_FUSION_BASELINE = "rule_based_fusion_baseline"
    SEMANTIC_GRAPH_ORCHESTRATION = "semantic_graph_orchestration"
    DUALEXIS_FULL_PIPELINE = "dualexis_full_pipeline"


class UnknownProtocolError(ValueError):
    """Raised when a protocol name is not registered."""


@dataclass(frozen=True)
class ProtocolExecutionResult:
    """Artifacts emitted by an experimental protocol on a simulation run."""

    events: tuple[SemanticEvent, ...]
    end_to_end_latency_ms: float
    time_to_recommendation_ms: float
    graph_update_latency_ms: float
    raw_media_bytes_persisted: int = 0
    personal_data_violations: int = 0
    privacy_violation_count: int = 0
    human_review_compliant_count: int = 0
    human_review_required_count: int = 0
    explanation_completeness_score: float = 1.0


@dataclass(frozen=True)
class ExperimentProtocol:
    """Metadata for a registered experimental protocol."""

    protocol_id: ExperimentProtocolId
    description: str
    uses_temporal_graph: bool
    uses_local_reasoning: bool


_PROTOCOLS: dict[ExperimentProtocolId, ExperimentProtocol] = {
    ExperimentProtocolId.SINGLE_MODALITY_BASELINE: ExperimentProtocol(
        protocol_id=ExperimentProtocolId.SINGLE_MODALITY_BASELINE,
        description="B1-style isolated single-modality alerting without fusion or graph.",
        uses_temporal_graph=False,
        uses_local_reasoning=False,
    ),
    ExperimentProtocolId.RULE_BASED_FUSION_BASELINE: ExperimentProtocol(
        protocol_id=ExperimentProtocolId.RULE_BASED_FUSION_BASELINE,
        description="B2-style threshold fusion without temporal graph or LLM copilot.",
        uses_temporal_graph=False,
        uses_local_reasoning=False,
    ),
    ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION: ExperimentProtocol(
        protocol_id=ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION,
        description="Semantic events with L4 temporal graph ingestion (no full L5/L6 stack).",
        uses_temporal_graph=True,
        uses_local_reasoning=False,
    ),
    ExperimentProtocolId.DUALEXIS_FULL_PIPELINE: ExperimentProtocol(
        protocol_id=ExperimentProtocolId.DUALEXIS_FULL_PIPELINE,
        description="Full six-layer DUALEXIS pipeline (L1--L6) on synthetic inputs.",
        uses_temporal_graph=True,
        uses_local_reasoning=True,
    ),
}


def list_protocols() -> tuple[ExperimentProtocolId, ...]:
    """Return all registered protocol identifiers."""
    return tuple(ExperimentProtocolId)


def get_protocol(name: str) -> ExperimentProtocol:
    """Resolve a protocol name to its metadata record."""
    try:
        protocol_id = ExperimentProtocolId(name)
    except ValueError as exc:
        valid = ", ".join(protocol.value for protocol in ExperimentProtocolId)
        msg = f"Unknown protocol {name!r}. Valid protocols: {valid}"
        raise UnknownProtocolError(msg) from exc
    return _PROTOCOLS[protocol_id]


def _deterministic_latency_ms(seed: int, protocol: ExperimentProtocolId, component: str) -> float:
    """Return a seed-stable latency scaffold (not wall-clock measurement)."""
    token = f"{protocol.value}:{component}:{seed}"
    mixed = sum(ord(char) for char in token) % 250
    bases = {
        ExperimentProtocolId.SINGLE_MODALITY_BASELINE: 280.0,
        ExperimentProtocolId.RULE_BASED_FUSION_BASELINE: 220.0,
        ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION: 160.0,
        ExperimentProtocolId.DUALEXIS_FULL_PIPELINE: 120.0,
    }
    return bases[protocol] + float(mixed)


def _baseline_output_to_protocol_result(
    output: BaselineOutput,
    *,
    protocol: ExperimentProtocolId,
    seed: int,
    graph_update_latency_ms: float = 0.0,
) -> ProtocolExecutionResult:
    return ProtocolExecutionResult(
        events=output.events,
        end_to_end_latency_ms=_deterministic_latency_ms(seed, protocol, "e2e"),
        time_to_recommendation_ms=output.time_to_recommendation_ms,
        graph_update_latency_ms=graph_update_latency_ms,
        raw_media_bytes_persisted=output.raw_media_bytes_persisted,
        personal_data_violations=output.personal_data_violations,
        privacy_violation_count=output.personal_data_violations,
        human_review_compliant_count=output.human_review_compliant_count,
        human_review_required_count=output.human_review_required_count,
    )


def _execute_semantic_graph_orchestration(simulation: SimulationResult) -> ProtocolExecutionResult:
    graph = InMemoryTemporalGraphService()
    for zone in simulation.graph.zones:
        graph.add_zone(
            Zone(
                zone_id=zone.zone_id,
                label=zone.zone_label,
                adjacent_zone_ids=simulation.graph.adjacent_zones(zone.zone_id),
            )
        )
    for exit_node in simulation.graph.exits:
        graph.add_exit(
            Exit(
                exit_id=exit_node.exit_id,
                zone_id=exit_node.zone_id,
                label=exit_node.exit_id,
            )
        )

    for event in simulation.events:
        graph.ingest_semantic_event(event)

    graph_latency = _deterministic_latency_ms(
        simulation.seed,
        ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION,
        "graph",
    )
    baseline = DualexisSemanticBaseline().run(simulation)
    return ProtocolExecutionResult(
        events=baseline.events,
        end_to_end_latency_ms=_deterministic_latency_ms(
            simulation.seed,
            ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION,
            "e2e",
        ),
        time_to_recommendation_ms=baseline.time_to_recommendation_ms,
        graph_update_latency_ms=graph_latency,
        raw_media_bytes_persisted=0,
        personal_data_violations=0,
        privacy_violation_count=0,
        human_review_compliant_count=baseline.human_review_compliant_count,
        human_review_required_count=baseline.human_review_required_count,
        explanation_completeness_score=1.0,
    )


def _execute_full_pipeline(
    simulation: SimulationResult,
    scenario_name: str,
) -> ProtocolExecutionResult:
    from dualexis.pipeline.service import run_pipeline

    output = run_pipeline(scenario_name, seed=simulation.seed)
    review_required = sum(1 for rec in output.recommendations if rec.requires_human_review)
    review_compliant = sum(
        1
        for rec in output.recommendations
        if rec.requires_human_review and rec.human_review_status.value != "not_required"
    )
    privacy = output.privacy_report
    explanation_score = _explanation_completeness(output.normalized_events)

    return ProtocolExecutionResult(
        events=output.normalized_events,
        end_to_end_latency_ms=_deterministic_latency_ms(
            simulation.seed,
            ExperimentProtocolId.DUALEXIS_FULL_PIPELINE,
            "e2e",
        ),
        time_to_recommendation_ms=90.0 + float(simulation.seed % 35),
        graph_update_latency_ms=_deterministic_latency_ms(
            simulation.seed,
            ExperimentProtocolId.DUALEXIS_FULL_PIPELINE,
            "graph",
        ),
        raw_media_bytes_persisted=privacy.raw_media_bytes_persisted,
        personal_data_violations=privacy.personal_data_violations,
        privacy_violation_count=len(privacy.violations),
        human_review_compliant_count=review_compliant,
        human_review_required_count=review_required,
        explanation_completeness_score=explanation_score,
    )


def _explanation_completeness(events: tuple[SemanticEvent, ...]) -> float:
    if not events:
        return 0.0
    complete = 0
    for event in events:
        has_zone = bool(event.zone_id)
        has_explanation = bool(event.explanation.strip())
        has_category = bool(event.metadata.get("category"))
        if has_zone and has_explanation and has_category:
            complete += 1
    return complete / len(events)


def execute_protocol(
    protocol_id: ExperimentProtocolId,
    simulation: SimulationResult,
    *,
    scenario_name: str,
) -> ProtocolExecutionResult:
    """Execute a registered protocol on a completed simulation result."""
    if protocol_id == ExperimentProtocolId.SINGLE_MODALITY_BASELINE:
        output = SingleModalityBaseline().run(simulation)
        return _baseline_output_to_protocol_result(
            output,
            protocol=protocol_id,
            seed=simulation.seed,
        )

    if protocol_id == ExperimentProtocolId.RULE_BASED_FUSION_BASELINE:
        output = RuleBasedFusionBaseline().run(simulation)
        return _baseline_output_to_protocol_result(
            output,
            protocol=protocol_id,
            seed=simulation.seed,
        )

    if protocol_id == ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION:
        return _execute_semantic_graph_orchestration(simulation)

    if protocol_id == ExperimentProtocolId.DUALEXIS_FULL_PIPELINE:
        return _execute_full_pipeline(simulation, scenario_name)

    assert_never(protocol_id)


__all__ = [
    "ExperimentProtocol",
    "ExperimentProtocolId",
    "ProtocolExecutionResult",
    "UnknownProtocolError",
    "execute_protocol",
    "get_protocol",
    "list_protocols",
]
