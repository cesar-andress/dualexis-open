"""Layer package structure — imports, interfaces, and service initialization."""

from __future__ import annotations

import importlib

import pytest

from apps.services import build_safety_orchestrator


@pytest.mark.unit
@pytest.mark.parametrize(
    ("package", "layer_attr"),
    [
        ("dualexis.privacy_runtime", "PRIVACY_RUNTIME_LAYER"),
        ("dualexis.edge_perception", "EDGE_PERCEPTION_LAYER"),
        ("dualexis.semantic_events", "SEMANTIC_EVENTS_LAYER"),
        ("dualexis.temporal_graph", "TEMPORAL_GRAPH_LAYER"),
        ("dualexis.local_reasoning", "LOCAL_REASONING_LAYER"),
        ("dualexis.orchestration", "ORCHESTRATION_LAYER"),
        ("dualexis.evaluation", "EVALUATION_LAYER"),
        ("dualexis.simulation", "SIMULATION_LAYER"),
    ],
)
def test_layer_package_imports(package: str, layer_attr: str) -> None:
    module = importlib.import_module(package)
    assert module.__doc__ is not None
    layer = getattr(module, layer_attr)
    assert layer.processes_events_only is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "subpackage",
    [
        "dualexis.privacy_runtime",
        "dualexis.edge_perception",
        "dualexis.semantic_events",
        "dualexis.temporal_graph",
        "dualexis.local_reasoning",
        "dualexis.orchestration",
        "dualexis.evaluation",
        "dualexis.simulation",
    ],
)
def test_layer_submodules_import(subpackage: str) -> None:
    for name in ("interfaces", "models", "service"):
        module = importlib.import_module(f"{subpackage}.{name}")
        assert module.__doc__ is not None


@pytest.mark.unit
def test_privacy_runtime_service_initializes() -> None:
    from dualexis.privacy_runtime import DefaultPrivacyRuntimeService, PrivacyRuntimeService

    service = DefaultPrivacyRuntimeService()
    assert isinstance(service, PrivacyRuntimeService)
    assert service.active_policy().allow_biometric_features is False


@pytest.mark.unit
def test_edge_perception_service_initializes() -> None:
    from dualexis.edge_perception import EdgePerceptionService, create_placeholder_service

    service = create_placeholder_service()
    assert isinstance(service, EdgePerceptionService)
    assert service.pipelines() == {}


@pytest.mark.unit
def test_semantic_events_service_initializes() -> None:
    from dualexis.semantic_events import DefaultSemanticEventService, SemanticEventService

    service = DefaultSemanticEventService()
    assert isinstance(service, SemanticEventService)


@pytest.mark.unit
def test_temporal_graph_service_initializes() -> None:
    from dualexis.temporal_graph import InMemoryTemporalGraphService, TemporalGraphService

    graph = InMemoryTemporalGraphService()
    assert isinstance(graph, TemporalGraphService)
    assert graph.size() == 0


@pytest.mark.unit
def test_local_reasoning_service_initializes() -> None:
    from dualexis.local_reasoning import (
        CopilotConfig,
        LocalReasoningService,
        PlaceholderLocalReasoningService,
    )

    service = PlaceholderLocalReasoningService(CopilotConfig())
    assert isinstance(service, LocalReasoningService)
    assert service.config.allow_raw_media_prompts is False


@pytest.mark.unit
def test_orchestration_service_initializes() -> None:
    from dualexis.orchestration import OrchestrationService
    from dualexis.orchestration.service import SafetyOrchestrator

    orchestrator = build_safety_orchestrator("edge-test-001", {})
    assert isinstance(orchestrator, OrchestrationService)
    assert isinstance(orchestrator, SafetyOrchestrator)


@pytest.mark.unit
def test_evaluation_service_initializes() -> None:
    from dualexis.evaluation import EvaluationService, PlaceholderEvaluationService

    service = PlaceholderEvaluationService()
    assert isinstance(service, EvaluationService)
    assert len(service.registered_metrics()) >= 1


@pytest.mark.unit
def test_simulation_service_initializes() -> None:
    from dualexis.simulation import DefaultSimulationService, SimulationScenario, SimulationService

    service = DefaultSimulationService()
    assert isinstance(service, SimulationService)
    batch = service.generate_batch(
        SimulationScenario.HALLWAY_ACOUSTIC,
        node_id="sim-001",
        zone_id="hall-a",
    )
    assert len(batch.frames) == 1
    assert batch.frames[0].payload_ref is None
