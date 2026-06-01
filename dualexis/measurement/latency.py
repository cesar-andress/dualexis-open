"""Instrumented pipeline latency measurement."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import cast
from uuid import uuid4

from dualexis.pipeline.models import PipelineOutput
from dualexis.pipeline.service import (
    create_default_pipeline_service,
    pipeline_inputs_from_scenario,
    semantic_event_from_safety,
    synthetic_frames_from_input,
)
from dualexis.privacy_runtime.service import DefaultPrivacyRuntimeService
from dualexis.schemas.audit import AuditAction
from dualexis.schemas.fusion import FusionInput
from dualexis.schemas.perception import PerceptionFrame
from dualexis.simulation.runner import SimulationResult, run_scenario


@dataclass
class StageTimings:
    """Wall-clock stage latencies in milliseconds."""

    event_generation_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    graph_update_latency_ms: float = 0.0
    reasoning_latency_ms: float = 0.0
    recommendation_latency_ms: float = 0.0
    end_to_end_latency_ms: float = 0.0


@dataclass
class InstrumentedRun:
    """Pipeline output paired with stage timings."""

    output: PipelineOutput
    timings: StageTimings
    simulation: SimulationResult


def _elapsed_ms(start: float) -> float:
    return max(0.0, (time.perf_counter() - start) * 1000.0)


def _filter_frames(
    frames: list[PerceptionFrame],
    *,
    drop_modality: str | None,
) -> list[PerceptionFrame]:
    if drop_modality is None:
        return frames
    return [frame for frame in frames if frame.modality.value != drop_modality]


async def _run_instrumented_pipeline(
    scenario_name: str,
    *,
    seed: int,
    simulation: SimulationResult | None = None,
    drop_modality: str | None = None,
) -> InstrumentedRun:
    """Execute the pipeline with per-stage wall-clock timing."""
    from dualexis.local_reasoning.models import ReasoningRequest
    from dualexis.orchestration.models import (
        HIGH_RISK_SEVERITIES,
        HumanReviewStatus,
        OrchestrationRecommendation,
    )
    from dualexis.pipeline.models import GraphUpdate
    from dualexis.privacy_runtime.models import TrustBoundary
    from dualexis.schemas.audit import AuditEntry

    timings = StageTimings()
    e2e_start = time.perf_counter()

    gen_start = time.perf_counter()
    sim = simulation or run_scenario(scenario_name, seed=seed)
    timings.event_generation_latency_ms = _elapsed_ms(gen_start)

    service = create_default_pipeline_service()
    privacy_runtime = cast(DefaultPrivacyRuntimeService, service._privacy)
    inputs = pipeline_inputs_from_scenario(scenario_name, seed=seed, simulation=sim)

    if hasattr(privacy_runtime, "reset_session_state"):
        privacy_runtime.reset_session_state()

    normalized_events = []
    recommendations = []
    graph_updates = []
    fusion_result = None

    for pipeline_input in inputs:
        zone_id = pipeline_input.synthetic_payload.get("zone_id", "hallway-a")
        now = pipeline_input.timestamp
        frames = _filter_frames(
            synthetic_frames_from_input(pipeline_input),
            drop_modality=drop_modality,
        )

        sanitized_frames: list[PerceptionFrame] = []
        for frame in frames:
            privacy_runtime.validate_frame(frame)
            sanitized_frames.append(privacy_runtime.sanitize_frame(frame))

        signals = await service._perception.process_frames(sanitized_frames)
        validated_signals = []
        for signal in signals:
            validated_signals.append(privacy_runtime.validate_signal(signal))

        fusion_start = time.perf_counter()
        fusion_input = FusionInput(
            node_id=service._node_id,
            zone_id=zone_id,
            window_start=now - timedelta(seconds=5),
            window_end=now,
            signals=tuple(validated_signals),
        )
        fusion_result = await service._semantic.fuse_signals(fusion_input)
        timings.fusion_latency_ms += _elapsed_ms(fusion_start)

        safety_event = service._semantic.build_safety_event(
            fusion_result,
            node_id=service._node_id,
            zone_id=zone_id,
        )
        validated_event = privacy_runtime.validate_event(safety_event)
        semantic_event = semantic_event_from_safety(validated_event, simulation=sim)
        normalized_events.append(semantic_event)

        graph_start = time.perf_counter()
        service._graph.add_event(validated_event)
        graph_updates.append(
            GraphUpdate(
                update_type="node_added",
                event_id=semantic_event.event_id,
                details={"zone_id": zone_id},
            )
        )
        timings.graph_update_latency_ms += _elapsed_ms(graph_start)

        if service._reasoning.is_available():
            event_uuid = semantic_event.event_id
            context = service._graph.get_context(event_uuid)
            reasoning_request = ReasoningRequest(
                request_id=str(uuid4()),
                event=validated_event,
                context_events=context,
            )
            privacy_runtime.check_egress(
                {"event_id": str(validated_event.event_id)},
                boundary=TrustBoundary.TB4_LLM_REASONING,
            )

            reasoning_start = time.perf_counter()
            reasoning_response = await service._reasoning.reason(reasoning_request)
            timings.reasoning_latency_ms += _elapsed_ms(reasoning_start)

            rec_start = time.perf_counter()
            requires_review = (
                semantic_event.severity.value in HIGH_RISK_SEVERITIES
                or reasoning_response.requires_human_review
            )
            review_status = (
                HumanReviewStatus.PENDING if requires_review else HumanReviewStatus.NOT_REQUIRED
            )
            recommendation = OrchestrationRecommendation(
                recommendation_id=uuid4(),
                based_on_events=(semantic_event.event_id,),
                target_zone_id=zone_id,
                action=reasoning_response.recommended_action.value,
                rationale=reasoning_response.explanation,
                severity=semantic_event.severity,
                requires_human_review=requires_review,
                human_review_status=review_status,
                created_at=now,
            )
            recommendations.append(recommendation)
            timings.recommendation_latency_ms += _elapsed_ms(rec_start)

        privacy_runtime.check_egress(
            validated_event.model_dump(mode="json"),
            boundary=TrustBoundary.TB5_NETWORK_EGRESS,
        )
        await service._publisher.publish(validated_event)
        await service._audit.log(
            AuditEntry(
                entry_id=str(uuid4()),
                action=AuditAction.EVENT_PUBLISHED,
                node_id=service._node_id,
                details={"published_event_id": str(validated_event.event_id)},
                event_id=semantic_event.event_id,
            )
        )

    for sim_event in sim.events:
        if sim_event.event_id not in {event.event_id for event in normalized_events}:
            normalized_events.append(sim_event)

    from dualexis.evaluation.report import run_evaluation

    evaluation_metrics = run_evaluation(
        scenario_name,
        "dualexis_semantic",
        seed=seed,
    ).metrics

    audit_records = await service._collect_audit_records()
    privacy_runtime.ensure_high_risk_audit(normalized_events, audit_records)
    privacy_report = privacy_runtime.build_report(
        high_risk_audit_satisfied=True,
        evaluation_metrics=evaluation_metrics,
    )

    await service._audit.log(
        AuditEntry(
            entry_id=str(uuid4()),
            action=AuditAction.PRIVACY_CHECK_PASSED,
            node_id=service._node_id,
            details={"policy_compliant": str(privacy_report.policy_compliant)},
        )
    )
    audit_records = await service._collect_audit_records()

    output = PipelineOutput(
        normalized_events=tuple(normalized_events),
        fusion_result=fusion_result,
        graph_updates=tuple(graph_updates),
        recommendations=tuple(recommendations),
        audit_records=audit_records,
        privacy_report=privacy_report,
    )
    timings.end_to_end_latency_ms = _elapsed_ms(e2e_start)
    return InstrumentedRun(output=output, timings=timings, simulation=sim)


def run_instrumented_pipeline(
    scenario_name: str,
    *,
    seed: int = 42,
    drop_modality: str | None = None,
) -> InstrumentedRun:
    """Synchronous wrapper for instrumented pipeline execution."""
    return asyncio.run(
        _run_instrumented_pipeline(scenario_name, seed=seed, drop_modality=drop_modality)
    )


@dataclass
class LatencyAggregate:
    """Mean stage latencies across repeated runs."""

    runs: int
    timings: StageTimings = field(default_factory=StageTimings)


def measure_latency(
    scenario_name: str,
    *,
    seed: int = 42,
    runs: int = 1,
) -> LatencyAggregate:
    """Run the instrumented pipeline ``runs`` times and return mean latencies."""
    if runs < 1:
        msg = "runs must be >= 1"
        raise ValueError(msg)

    totals = StageTimings()
    for run_index in range(runs):
        run_seed = seed if runs == 1 else seed + run_index
        result = run_instrumented_pipeline(scenario_name, seed=run_seed)
        totals.event_generation_latency_ms += result.timings.event_generation_latency_ms
        totals.fusion_latency_ms += result.timings.fusion_latency_ms
        totals.graph_update_latency_ms += result.timings.graph_update_latency_ms
        totals.reasoning_latency_ms += result.timings.reasoning_latency_ms
        totals.recommendation_latency_ms += result.timings.recommendation_latency_ms
        totals.end_to_end_latency_ms += result.timings.end_to_end_latency_ms

    count = float(runs)
    return LatencyAggregate(
        runs=runs,
        timings=StageTimings(
            event_generation_latency_ms=totals.event_generation_latency_ms / count,
            fusion_latency_ms=totals.fusion_latency_ms / count,
            graph_update_latency_ms=totals.graph_update_latency_ms / count,
            reasoning_latency_ms=totals.reasoning_latency_ms / count,
            recommendation_latency_ms=totals.recommendation_latency_ms / count,
            end_to_end_latency_ms=totals.end_to_end_latency_ms / count,
        ),
    )


__all__ = [
    "InstrumentedRun",
    "LatencyAggregate",
    "StageTimings",
    "measure_latency",
    "run_instrumented_pipeline",
]
