"""End-to-end DUALEXIS pipeline orchestration (synthetic inputs only)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from dualexis.audit.logger import InMemoryAuditLogger
from dualexis.core.interfaces import AuditLogger, EventPublisher
from dualexis.edge_perception.interfaces import EdgePerceptionService
from dualexis.evaluation.report import run_evaluation
from dualexis.local_reasoning.interfaces import LocalReasoningService
from dualexis.local_reasoning.models import ReasoningRequest
from dualexis.orchestration.models import (
    HIGH_RISK_SEVERITIES,
    HumanReviewStatus,
    OrchestrationRecommendation,
    SeverityLevel,
)
from dualexis.pipeline.config import DEFAULT_PIPELINE_RUN_CONFIG, PipelineRunConfig
from dualexis.pipeline.interfaces import PipelineService
from dualexis.pipeline.models import (
    GraphUpdate,
    PipelineInput,
    PipelineOutput,
    PipelineSourceType,
)
from dualexis.privacy_runtime.interfaces import PrivacyRuntimeService
from dualexis.privacy_runtime.models import PrivacyLevel as DomainPrivacyLevel
from dualexis.privacy_runtime.models import TrustBoundary
from dualexis.schemas.audit import AuditAction, AuditEntry
from dualexis.schemas.domain import FusionResult, SafetyEvent
from dualexis.schemas.events import EventSeverity
from dualexis.schemas.fusion import FusionInput
from dualexis.schemas.perception import Modality, PerceptionFrame
from dualexis.semantic_events.interfaces import SemanticEventService
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent
from dualexis.simulation.runner import SimulationResult, run_scenario
from dualexis.temporal_graph.interfaces import TemporalGraphService

_SCHEMA_PRIVACY_TO_DOMAIN: dict[str, DomainPrivacyLevel] = {
    "ephemeral": DomainPrivacyLevel.EPHEMERAL,
    "internal": DomainPrivacyLevel.SEMANTIC_ONLY,
    "restricted": DomainPrivacyLevel.AUDIT_ONLY,
    "semantic_only": DomainPrivacyLevel.SEMANTIC_ONLY,
    "aggregated": DomainPrivacyLevel.AGGREGATED,
    "audit_only": DomainPrivacyLevel.AUDIT_ONLY,
}

_SCHEMA_TO_DOMAIN_EVENT_TYPE: dict[str, EventType] = {
    "zone_activity": EventType.NORMAL_FLOW,
    "crowd_activity": EventType.CROWD_ACCELERATION,
    "acoustic_anomaly": EventType.AUDIO_STRESS_SIGNAL,
    "environmental_sensor": EventType.EXIT_BLOCKAGE,
    "multimodal_fusion": EventType.MULTIMODAL_CONFLICT,
    "unknown": EventType.UNKNOWN,
}

_SEVERITY_TO_DOMAIN: dict[EventSeverity, SeverityLevel] = {
    EventSeverity.INFO: SeverityLevel.LOW,
    EventSeverity.LOW: SeverityLevel.LOW,
    EventSeverity.MEDIUM: SeverityLevel.MEDIUM,
    EventSeverity.HIGH: SeverityLevel.HIGH,
    EventSeverity.CRITICAL: SeverityLevel.CRITICAL,
}


def _stable_uuid(seed: int, label: str, index: int = 0) -> UUID:
    """Derive a deterministic UUID for reproducible pipeline runs."""
    return uuid5(NAMESPACE_URL, f"dualexis-pipeline:{seed}:{label}:{index}")


def _severity_from_simulation(simulation: SimulationResult | None) -> SeverityLevel:
    if simulation is None or not simulation.events:
        return SeverityLevel.MEDIUM
    order = [
        SeverityLevel.LOW,
        SeverityLevel.MEDIUM,
        SeverityLevel.HIGH,
        SeverityLevel.CRITICAL,
    ]
    max_index = max(order.index(event.severity) for event in simulation.events)
    return order[max_index]


def semantic_event_from_safety(
    event: SafetyEvent,
    *,
    simulation: SimulationResult | None = None,
) -> SemanticEvent:
    """Map a legacy SafetyEvent to the canonical SemanticEvent domain model."""
    schema_type = event.event_type.value
    domain_type = _SCHEMA_TO_DOMAIN_EVENT_TYPE.get(schema_type, EventType.UNKNOWN)
    severity = _SEVERITY_TO_DOMAIN.get(event.severity, SeverityLevel.MEDIUM)
    if simulation is not None and simulation.events:
        severity = _severity_from_simulation(simulation)

    category = event.descriptors[0].category if event.descriptors else "fused_event"
    modalities = (
        ",".join(event.descriptors[0].source_modalities)
        if event.descriptors and event.descriptors[0].source_modalities
        else "video,audio,sensor"
    )

    return SemanticEvent(
        event_id=event.event_id if isinstance(event.event_id, UUID) else UUID(str(event.event_id)),
        event_type=domain_type,
        source=EventSource.SIMULATOR,
        zone_id=event.zone_id,
        timestamp=event.timestamp,
        confidence=event.confidence.value,
        severity=severity,
        explanation=event.explanation,
        privacy_level=_SCHEMA_PRIVACY_TO_DOMAIN.get(
            event.privacy_level.value,
            DomainPrivacyLevel.SEMANTIC_ONLY,
        ),
        metadata={"category": category, "modalities": modalities},
    )


def pipeline_inputs_from_scenario(
    scenario_name: str,
    *,
    seed: int,
    simulation: SimulationResult | None = None,
) -> tuple[PipelineInput, ...]:
    """Build deterministic synthetic pipeline inputs from a simulation scenario."""
    sim = simulation or run_scenario(scenario_name, seed=seed)
    if not sim.events:
        zone_id = "hallway-a"
        timestamp = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    else:
        anchor = sim.events[0]
        zone_id = anchor.zone_id
        timestamp = anchor.timestamp

    final_state = sim.final_state
    density = "0.25"
    activity = "0.20"
    audio_stress = "0.10"
    if final_state is not None:
        density = f"{final_state.zone_density.get(zone_id, 0.25):.4f}"
        activity = f"{final_state.zone_activity.get(zone_id, 0.20):.4f}"
        audio_stress = f"{final_state.zone_audio_stress.get(zone_id, 0.10):.4f}"

    return (
        PipelineInput(
            source_id=f"pipeline-sim-{seed}",
            source_type=PipelineSourceType.SIMULATOR,
            timestamp=timestamp,
            synthetic_payload={
                "zone_id": zone_id,
                "scenario": scenario_name,
                "density": density,
                "activity": activity,
                "audio_stress": audio_stress,
            },
            metadata={"seed": str(seed), "scenario": scenario_name},
        ),
    )


def synthetic_frames_from_input(pipeline_input: PipelineInput) -> list[PerceptionFrame]:
    """Convert synthetic payload metadata to ephemeral perception frames (no raw media)."""
    zone_id = pipeline_input.synthetic_payload.get("zone_id", "hallway-a")
    node_id = pipeline_input.source_id
    timestamp = pipeline_input.timestamp
    return [
        PerceptionFrame(
            modality=Modality.VIDEO,
            node_id=node_id,
            zone_id=zone_id,
            timestamp=timestamp,
            payload_ref=None,
        ),
        PerceptionFrame(
            modality=Modality.AUDIO,
            node_id=node_id,
            zone_id=zone_id,
            timestamp=timestamp,
            payload_ref=None,
        ),
        PerceptionFrame(
            modality=Modality.SENSOR,
            node_id=node_id,
            zone_id=zone_id,
            timestamp=timestamp,
            payload_ref=None,
        ),
    ]


class DefaultPipelineService(PipelineService):
    """Orchestrates privacy, perception, fusion, graph, reasoning, evaluation, and audit."""

    def __init__(
        self,
        *,
        node_id: str,
        privacy_runtime: PrivacyRuntimeService,
        edge_perception: EdgePerceptionService,
        semantic_events: SemanticEventService,
        temporal_graph: TemporalGraphService,
        local_reasoning: LocalReasoningService,
        event_publisher: EventPublisher,
        audit_logger: AuditLogger,
    ) -> None:
        self._node_id = node_id
        self._privacy = privacy_runtime
        self._perception = edge_perception
        self._semantic = semantic_events
        self._graph = temporal_graph
        self._reasoning = local_reasoning
        self._publisher = event_publisher
        self._audit = audit_logger
        self._trust_boundaries: list[str] = []

    async def run(
        self,
        inputs: Sequence[PipelineInput],
        *,
        scenario_name: str | None = None,
        seed: int | None = None,
        simulation: SimulationResult | None = None,
        run_config: PipelineRunConfig | None = None,
    ) -> PipelineOutput:
        config = run_config or DEFAULT_PIPELINE_RUN_CONFIG
        if not inputs:
            msg = "At least one PipelineInput is required"
            raise ValueError(msg)

        if simulation is None and scenario_name is not None and seed is not None:
            simulation = run_scenario(scenario_name, seed=seed)

        if hasattr(self._privacy, "reset_session_state"):
            self._privacy.reset_session_state()

        graph_updates: list[GraphUpdate] = []
        normalized_events: list[SemanticEvent] = []
        recommendations: list[OrchestrationRecommendation] = []
        fusion_result: FusionResult | None = None
        audit_index = 0
        sssg_service = None
        if config.enable_sssg and scenario_name is not None:
            from dualexis.sssg.service import SemanticSafetyStateGraphService

            sssg_service = SemanticSafetyStateGraphService(
                scenario_id=scenario_name,
                seed=seed or 0,
            )
        peer_zone_ids = (
            tuple(z.zone_id for z in simulation.graph.zones)
            if simulation is not None
            else tuple()
        )

        def stable_id(label: str) -> UUID:
            nonlocal audit_index
            if seed is None:
                return uuid4()
            stable = _stable_uuid(seed, label, audit_index)
            audit_index += 1
            return stable

        def audit_timestamp(observation_time: datetime) -> datetime | None:
            return observation_time if seed is not None else None

        def make_audit_entry(
            *,
            label: str,
            action: AuditAction,
            observation_time: datetime,
            details: dict[str, str],
            event_id: UUID | None = None,
        ) -> AuditEntry:
            entry_kwargs: dict[str, object] = {
                "entry_id": str(stable_id(label)),
                "action": action,
                "node_id": self._node_id,
                "details": details,
            }
            stable_ts = audit_timestamp(observation_time)
            if stable_ts is not None:
                entry_kwargs["timestamp"] = stable_ts
            if event_id is not None:
                entry_kwargs["event_id"] = event_id
            return AuditEntry(**entry_kwargs)  # type: ignore[arg-type]

        for pipeline_input in inputs:
            zone_id = pipeline_input.synthetic_payload.get("zone_id", "hallway-a")
            now = pipeline_input.timestamp
            frames = synthetic_frames_from_input(pipeline_input)

            sanitized_frames: list[PerceptionFrame] = []
            for frame in frames:
                if config.enable_privacy_runtime:
                    self._privacy.validate_frame(frame)
                    sanitized_frames.append(self._privacy.sanitize_frame(frame))
                else:
                    sanitized_frames.append(frame)
            frames = sanitized_frames
            if config.enable_privacy_runtime:
                self._record_boundary(TrustBoundary.TB1_EPHEMERAL_BUFFER)

            signals = await self._perception.process_frames(frames)
            validated_signals = []
            for signal_index, signal in enumerate(signals):
                validated = (
                    self._privacy.validate_signal(signal)
                    if config.enable_privacy_runtime
                    else signal
                )
                if seed is not None:
                    validated = validated.model_copy(
                        update={
                            "signal_id": str(
                                _stable_uuid(
                                    seed,
                                    f"signal-{validated.modality.value}",
                                    signal_index,
                                )
                            )
                        }
                    )
                validated_signals.append(validated)
                await self._audit.log(
                    make_audit_entry(
                        label="audit-perception",
                        action=AuditAction.PERCEPTION_PROCESSED,
                        observation_time=now,
                        details={
                            "signal_id": validated.signal_id,
                            "modality": validated.modality.value,
                        },
                    )
                )
            if config.enable_privacy_runtime:
                self._record_boundary(TrustBoundary.TB2_PERCEPTION_OUTPUT)

            fusion_input = FusionInput(
                node_id=self._node_id,
                zone_id=zone_id,
                window_start=now - timedelta(seconds=5),
                window_end=now,
                signals=tuple(validated_signals),
            )
            fusion_result = await self._semantic.fuse_signals(fusion_input)
            if seed is not None:
                fusion_result = fusion_result.model_copy(
                    update={
                        "fusion_id": str(_stable_uuid(seed, "fusion", 0)),
                        "signal_ids": tuple(signal.signal_id for signal in validated_signals),
                        "timestamp": now,
                    }
                )
            await self._audit.log(
                make_audit_entry(
                    label="audit-fusion",
                    action=AuditAction.FUSION_COMPLETED,
                    observation_time=now,
                    details={"fusion_id": fusion_result.fusion_id},
                )
            )
            if config.enable_privacy_runtime:
                self._record_boundary(TrustBoundary.TB3_EVENT_PUBLICATION)

            safety_event = self._semantic.build_safety_event(
                fusion_result,
                node_id=self._node_id,
                zone_id=zone_id,
            )
            if seed is not None:
                safety_event = safety_event.model_copy(
                    update={
                        "event_id": _stable_uuid(seed, "safety-event", 0),
                        "timestamp": now,
                    }
                )
            validated_event = (
                self._privacy.validate_event(safety_event)
                if config.enable_privacy_runtime
                else safety_event
            )
            semantic_event = semantic_event_from_safety(validated_event, simulation=simulation)
            if not config.enable_explanation_layer:
                semantic_event = semantic_event.model_copy(
                    update={"explanation": "", "metadata": {**semantic_event.metadata, "category": ""}}
                )
            if sssg_service is not None:
                transition = sssg_service.ingest_semantic_event(
                    semantic_event,
                    peer_zones=peer_zone_ids or (zone_id,),
                )
                if transition is not None:
                    semantic_event = semantic_event.model_copy(
                        update={
                            "explanation": transition.explanation,
                            "metadata": {
                                **semantic_event.metadata,
                                "safety_state": transition.to_state.value,
                                "prior_safety_state": transition.from_state.value,
                            },
                        }
                    )
            normalized_events.append(semantic_event)

            if config.enable_temporal_graph:
                self._graph.add_event(validated_event)
                graph_updates.append(
                    GraphUpdate(
                        update_type="node_added",
                        event_id=semantic_event.event_id,
                        details={"zone_id": zone_id},
                    )
                )

            if config.enable_explanation_layer and self._reasoning.is_available():
                event_uuid = semantic_event.event_id
                context = self._graph.get_context(event_uuid)
                reasoning_request = ReasoningRequest(
                    request_id=str(stable_id("reasoning-request")),
                    event=validated_event,
                    context_events=context,
                )
                if config.enable_privacy_runtime:
                    self._privacy.check_egress(
                        {"event_id": str(validated_event.event_id)},
                        boundary=TrustBoundary.TB4_LLM_REASONING,
                    )
                    self._record_boundary(TrustBoundary.TB4_LLM_REASONING)
                reasoning_response = await self._reasoning.reason(reasoning_request)

                requires_review = (
                    semantic_event.severity.value in HIGH_RISK_SEVERITIES
                    or reasoning_response.requires_human_review
                )
                review_status = (
                    HumanReviewStatus.PENDING if requires_review else HumanReviewStatus.NOT_REQUIRED
                )
                if semantic_event.severity.value in HIGH_RISK_SEVERITIES:
                    review_status = HumanReviewStatus.PENDING

                state_rationale = (
                    sssg_service.graph.transitions[-1].explanation
                    if sssg_service is not None and sssg_service.graph.transitions
                    else reasoning_response.explanation
                )
                recommendation = OrchestrationRecommendation(
                    recommendation_id=stable_id("recommendation"),
                    based_on_events=(semantic_event.event_id,),
                    target_zone_id=zone_id,
                    action=reasoning_response.recommended_action.value,
                    rationale=state_rationale,
                    severity=semantic_event.severity,
                    requires_human_review=requires_review
                    or semantic_event.severity.value in HIGH_RISK_SEVERITIES,
                    human_review_status=review_status,
                    created_at=now,
                )
                recommendations.append(recommendation)

                await self._audit.log(
                    make_audit_entry(
                        label="audit-reasoning",
                        action=AuditAction.REASONING_INVOKED,
                        observation_time=now,
                        details={"recommended_action": reasoning_response.recommended_action.value},
                        event_id=event_uuid,
                    )
                )

            if config.enable_privacy_runtime:
                self._privacy.check_egress(
                    validated_event.model_dump(mode="json"),
                    boundary=TrustBoundary.TB5_NETWORK_EGRESS,
                )
                self._record_boundary(TrustBoundary.TB5_NETWORK_EGRESS)
            await self._publisher.publish(validated_event)
            await self._audit.log(
                make_audit_entry(
                    label="audit-published",
                    action=AuditAction.EVENT_PUBLISHED,
                    observation_time=now,
                    details={"published_event_id": str(validated_event.event_id)},
                )
            )

        observation_time = inputs[-1].timestamp

        if simulation is not None:
            for sim_event in simulation.events:
                if sim_event.event_id not in {event.event_id for event in normalized_events}:
                    normalized_events.append(sim_event)

        evaluation_metrics = None
        if scenario_name is not None and seed is not None:
            evaluation_metrics = run_evaluation(
                scenario_name,
                "dualexis_semantic",
                seed=seed,
            ).metrics

        audit_records = await self._collect_audit_records()
        self._privacy.ensure_high_risk_audit(normalized_events, audit_records)
        privacy_report = self._privacy.build_report(
            high_risk_audit_satisfied=True,
            evaluation_metrics=evaluation_metrics,
        )

        await self._audit.log(
            make_audit_entry(
                label="audit-privacy",
                action=AuditAction.PRIVACY_CHECK_PASSED,
                observation_time=observation_time,
                details={"policy_compliant": str(privacy_report.policy_compliant)},
            )
        )
        audit_records = await self._collect_audit_records()

        state_transition_trace = None
        if config.enable_sssg and scenario_name is not None and seed is not None:
            from dualexis.sssg.runner import build_sssg_trace_from_scenario

            state_transition_trace = build_sssg_trace_from_scenario(
                scenario_name,
                seed=seed,
            )

        return PipelineOutput(
            normalized_events=tuple(normalized_events),
            fusion_result=fusion_result,
            graph_updates=tuple(graph_updates),
            recommendations=tuple(recommendations),
            audit_records=audit_records,
            privacy_report=privacy_report,
            state_transition_trace=state_transition_trace,
        )

    def _record_boundary(self, boundary: TrustBoundary) -> None:
        if boundary.value not in self._trust_boundaries:
            self._trust_boundaries.append(boundary.value)

    async def _collect_audit_records(self) -> tuple[AuditEntry, ...]:
        if isinstance(self._audit, InMemoryAuditLogger):
            return tuple(self._audit._entries)
        entries = await self._audit.query(limit=10_000)
        return tuple(entries)


def create_default_pipeline_service(
    node_id: str = "pipeline-edge-001",
    *,
    publisher: EventPublisher | None = None,
    audit_logger: InMemoryAuditLogger | None = None,
    run_config: PipelineRunConfig | None = None,
) -> DefaultPipelineService:
    """Construct a pipeline wired with default L1--L6 placeholder services."""
    from dualexis.runtime.in_memory import InMemoryEventPublisher
    from dualexis.local_reasoning.service import PlaceholderLocalReasoningService
    from dualexis.perception.audio.pipeline import AudioPerceptionPipeline
    from dualexis.perception.sensors.pipeline import SensorPerceptionPipeline
    from dualexis.perception.video.pipeline import VideoPerceptionPipeline
    from dualexis.privacy_runtime.pass_through import PassThroughPrivacyRuntimeService
    from dualexis.privacy_runtime.service import DefaultPrivacyRuntimeService

    config = run_config or DEFAULT_PIPELINE_RUN_CONFIG
    privacy_runtime = (
        DefaultPrivacyRuntimeService()
        if config.enable_privacy_runtime
        else PassThroughPrivacyRuntimeService()
    )
    from dualexis.semantic_events.service import DefaultSemanticEventService
    from dualexis.temporal_graph.service import InMemoryTemporalGraphService

    audit = audit_logger or InMemoryAuditLogger()
    pub = publisher or InMemoryEventPublisher()
    pipelines = {
        Modality.VIDEO.value: VideoPerceptionPipeline(node_id),
        Modality.AUDIO.value: AudioPerceptionPipeline(node_id),
        Modality.SENSOR.value: SensorPerceptionPipeline(node_id),
    }
    from dualexis.edge_perception.service import DefaultEdgePerceptionService

    return DefaultPipelineService(
        node_id=node_id,
        privacy_runtime=privacy_runtime,
        edge_perception=DefaultEdgePerceptionService(pipelines),
        semantic_events=DefaultSemanticEventService(),
        temporal_graph=InMemoryTemporalGraphService(),
        local_reasoning=PlaceholderLocalReasoningService(),
        event_publisher=pub,
        audit_logger=audit,
    )


def run_pipeline(
    scenario_name: str,
    *,
    seed: int = 42,
    run_config: PipelineRunConfig | None = None,
) -> PipelineOutput:
    """Run the end-to-end pipeline for a simulation scenario (synthetic inputs only)."""
    config = run_config or DEFAULT_PIPELINE_RUN_CONFIG
    simulation = run_scenario(scenario_name, seed=seed)
    service = create_default_pipeline_service(run_config=config)
    inputs = pipeline_inputs_from_scenario(scenario_name, seed=seed, simulation=simulation)
    return asyncio.run(
        service.run(
            inputs,
            scenario_name=scenario_name,
            seed=seed,
            simulation=simulation,
            run_config=config,
        )
    )


__all__ = [
    "DefaultPipelineService",
    "create_default_pipeline_service",
    "pipeline_inputs_from_scenario",
    "run_pipeline",
    "semantic_event_from_safety",
    "synthetic_frames_from_input",
]
