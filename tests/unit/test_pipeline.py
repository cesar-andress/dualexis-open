"""Unit tests for the end-to-end DUALEXIS pipeline."""

from __future__ import annotations

import json

import pytest

from dualexis.orchestration.models import HumanReviewStatus, SeverityLevel
from dualexis.pipeline import run_pipeline
from dualexis.pipeline.models import PipelineOutput
from dualexis.pipeline.service import (
    create_default_pipeline_service,
    pipeline_inputs_from_scenario,
    synthetic_frames_from_input,
)
from dualexis.simulation.scenario import UnknownScenarioError


@pytest.mark.unit
def test_synthetic_frames_have_no_payload_ref() -> None:
    inputs = pipeline_inputs_from_scenario("normal_flow", seed=1)
    frames = synthetic_frames_from_input(inputs[0])
    assert len(frames) == 3
    assert all(frame.payload_ref is None for frame in frames)


@pytest.mark.unit
def test_pipeline_runs_end_to_end() -> None:
    output = run_pipeline("exit_blockage", seed=42)
    assert isinstance(output, PipelineOutput)
    assert output.normalized_events
    assert output.fusion_result is not None
    assert output.graph_updates
    assert output.recommendations
    assert output.audit_records
    assert output.privacy_report.policy_compliant is True


@pytest.mark.unit
def test_no_raw_media_persisted() -> None:
    output = run_pipeline("normal_flow", seed=7)
    assert output.privacy_report.raw_media_persisted is False
    assert output.privacy_report.raw_media_bytes_persisted == 0
    for event in output.normalized_events:
        assert event.raw_media_persisted is False


@pytest.mark.unit
def test_high_risk_recommendations_require_human_review() -> None:
    output = run_pipeline("evacuation_recommendation", seed=42)
    high_recs = [
        rec
        for rec in output.recommendations
        if rec.severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
    ]
    assert high_recs, "expected at least one high-risk recommendation for evacuation scenario"
    for rec in high_recs:
        assert rec.requires_human_review is True
        assert rec.human_review_status != HumanReviewStatus.APPROVED


@pytest.mark.unit
def test_deterministic_pipeline_output() -> None:
    first = run_pipeline("crowd_acceleration", seed=99)
    second = run_pipeline("crowd_acceleration", seed=99)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


@pytest.mark.unit
def test_audit_records_generated() -> None:
    output = run_pipeline("audio_stress_signal", seed=42)
    actions = {entry.action.value for entry in output.audit_records}
    assert "perception_processed" in actions
    assert "fusion_completed" in actions
    assert "event_published" in actions


@pytest.mark.unit
def test_privacy_report_generated() -> None:
    output = run_pipeline("multimodal_conflict", seed=42)
    report = output.privacy_report
    assert report.trust_boundaries_passed
    assert report.evaluation_metrics is not None
    assert report.personal_data_violations == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_service_directly() -> None:
    service = create_default_pipeline_service(node_id="test-pipeline")
    inputs = pipeline_inputs_from_scenario("exit_blockage", seed=5)
    output = await service.run(inputs, scenario_name="exit_blockage", seed=5)
    assert output.normalized_events


@pytest.mark.unit
def test_invalid_scenario_raises() -> None:
    with pytest.raises(UnknownScenarioError):
        run_pipeline("not_a_scenario", seed=1)


@pytest.mark.unit
def test_pipeline_json_serializable() -> None:
    output = run_pipeline("exit_blockage", seed=42)
    json.dumps(output.model_dump(mode="json"))
