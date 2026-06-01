"""Tests for the DUALEXIS edge runtime."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.edge_runtime import collect_health, load_edge_node_config, run_node
from dualexis.edge_runtime.models import EdgeNodeState
from dualexis.edge_runtime.node import EdgeNode
from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "infrastructure" / "edge" / "node.yaml"
)


def _sample_event(**overrides: object) -> SemanticEvent:
    base = SemanticEvent(
        event_id=uuid4(),
        event_type=EventType.EXIT_BLOCKAGE,
        source=EventSource.SIMULATOR,
        zone_id="hallway-a",
        timestamp=datetime.now(tz=UTC),
        confidence=0.9,
        severity=SeverityLevel.HIGH,
        explanation="Synthetic exit blockage signal",
        privacy_level=PrivacyLevel.SEMANTIC_ONLY,
        metadata={"category": "exit_blockage"},
    )
    if not overrides:
        return base
    return base.model_copy(update=overrides)


@pytest.mark.unit
def test_edge_node_emits_semantic_events_only() -> None:
    config = load_edge_node_config(CONFIG_PATH)
    node = EdgeNode(config)
    node.start()

    event = _sample_event()
    emitted = node.emit_event(event)

    assert isinstance(emitted, SemanticEvent)
    assert emitted.raw_media_persisted is False
    assert emitted.source in EventSource
    assert len(node.emitted_events()) == 1


@pytest.mark.unit
def test_raw_media_is_blocked() -> None:
    config = load_edge_node_config(CONFIG_PATH)
    node = EdgeNode(config)
    node.start()

    tainted = _sample_event(metadata={"raw_video": "file:///tmp/frame.bin"})
    with pytest.raises(PrivacyViolationError):
        node.emit_event(tainted)

    assert node.telemetry.snapshot().emissions_blocked >= 1


@pytest.mark.unit
def test_health_status_is_serializable() -> None:
    node = run_node(CONFIG_PATH)
    health = collect_health(node)
    payload = json.loads(json.dumps(health.model_dump(mode="json")))
    assert payload["node_id"] == node.config.node_id
    assert "checks" in payload
    assert "gpu" in payload
    assert isinstance(payload["healthy"], bool)


@pytest.mark.unit
def test_privacy_policy_enforced_before_emission() -> None:
    config = load_edge_node_config(CONFIG_PATH)
    node = EdgeNode(config)
    node.start()

    biometric = SemanticEvent.model_construct(
        event_id=uuid4(),
        event_type=EventType.EXIT_BLOCKAGE,
        source=EventSource.SIMULATOR,
        zone_id="hallway-a",
        timestamp=datetime.now(tz=UTC),
        confidence=0.9,
        severity=SeverityLevel.HIGH,
        explanation="Synthetic exit blockage signal",
        privacy_level=PrivacyLevel.SEMANTIC_ONLY,
        raw_media_persisted=False,
        metadata={"face_id": "blocked-123"},
    )
    with pytest.raises(PrivacyViolationError):
        node.emit_event(biometric)

    clean = _sample_event()
    node.emit_event(clean)
    assert node.telemetry.snapshot().emissions_total == 1


@pytest.mark.unit
def test_stopped_node_status_without_run() -> None:
    config = load_edge_node_config(CONFIG_PATH)
    status = EdgeNode(config).status()
    assert status.state == EdgeNodeState.STOPPED


@pytest.mark.unit
def test_health_without_running_node_is_not_healthy() -> None:
    config = load_edge_node_config(CONFIG_PATH)
    health = collect_health(EdgeNode(config))
    assert health.healthy is False
