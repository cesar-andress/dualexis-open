"""Integration tests for temporal graph and reasoning experiment protocols."""

from __future__ import annotations

import pytest

from dualexis.evaluation import execute_protocol, run_experiment
from dualexis.evaluation.protocol import ExperimentProtocolId
from dualexis.simulation import run_scenario
from dualexis.temporal_graph.service import InMemoryTemporalGraphService


@pytest.mark.integration
def test_semantic_graph_orchestration_ingests_events() -> None:
    simulation = run_scenario("exit_blockage", seed=42)
    result = execute_protocol(
        ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION,
        simulation,
        scenario_name="exit_blockage",
    )
    assert len(result.events) >= 1
    assert result.graph_update_latency_ms > 0.0


@pytest.mark.integration
def test_graph_service_reasoning_context_after_ingest() -> None:
    simulation = run_scenario("exit_blockage", seed=42)
    graph = InMemoryTemporalGraphService()
    anchor = simulation.events[0]
    for event in simulation.events:
        graph.ingest_semantic_event(event)
    context = graph.get_reasoning_context(anchor.event_id)
    assert context.anchor_event_id == anchor.event_id
    assert len(context.events) >= 1


@pytest.mark.integration
def test_graph_protocol_experiment_metrics() -> None:
    report = run_experiment("exit_blockage", "semantic_graph_orchestration", seed=42)
    assert report.metrics.graph_update_latency_ms > 0.0
    assert report.metrics.event_detection_accuracy >= 0.0


@pytest.mark.integration
def test_full_pipeline_experiment_includes_graph_latency() -> None:
    report = run_experiment("exit_blockage", "dualexis_full_pipeline", seed=42)
    assert report.metrics.graph_update_latency_ms > 0.0
    assert report.metrics.time_to_recommendation_ms > 0.0
