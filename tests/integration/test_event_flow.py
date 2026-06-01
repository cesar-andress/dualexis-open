"""Integration tests for the safety orchestration pipeline."""

from __future__ import annotations

import pytest

from dualexis.runtime.in_memory import build_safety_orchestrator
from dualexis.audit.logger import InMemoryAuditLogger
from dualexis.orchestration.service import SafetyOrchestrator
from dualexis.perception.audio.pipeline import AudioPerceptionPipeline
from dualexis.perception.video.pipeline import VideoPerceptionPipeline
from dualexis.schemas.events import EventStatus
from dualexis.schemas.perception import Modality, PerceptionFrame


@pytest.fixture
def orchestrator() -> SafetyOrchestrator:
    node_id = "edge-test-001"
    audit = InMemoryAuditLogger()
    return build_safety_orchestrator(
        node_id,
        {
            Modality.VIDEO.value: VideoPerceptionPipeline(node_id),
            Modality.AUDIO.value: AudioPerceptionPipeline(node_id),
        },
        audit_logger=audit,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_event_flow(orchestrator: SafetyOrchestrator) -> None:
    node_id = "edge-test-001"
    zone_id = "hallway-a"
    frames = [
        PerceptionFrame(modality=Modality.VIDEO, node_id=node_id, zone_id=zone_id),
        PerceptionFrame(modality=Modality.AUDIO, node_id=node_id, zone_id=zone_id),
    ]
    event = await orchestrator.process_frames(frames, zone_id=zone_id)
    assert event.zone_id == zone_id
    assert event.status == EventStatus.REASONED
    assert len(event.descriptors) >= 1
    assert event.recommendation is not None
    assert event.recommendation.explanation


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_trail_populated(orchestrator: SafetyOrchestrator) -> None:
    node_id = "edge-test-001"
    frames = [PerceptionFrame(modality=Modality.VIDEO, node_id=node_id, zone_id="hallway-a")]
    await orchestrator.process_frames(frames, zone_id="hallway-a")
    entries = await orchestrator._audit.query(limit=50)
    assert len(entries) >= 2
    assert all(e.integrity_hash for e in entries)
