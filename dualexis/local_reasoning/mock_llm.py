"""Deterministic mock LLM reasoner for L5 local reasoning."""

from __future__ import annotations

from dualexis.local_reasoning.interfaces import Reasoner
from dualexis.local_reasoning.models import (
    LocalReasoningInput,
    LocalReasoningOutput,
    requires_human_review_for_severity,
    validate_reasoning_payload,
)
from dualexis.local_reasoning.prompt_templates import build_structured_prompt
from dualexis.orchestration.models import SeverityLevel
from dualexis.schemas.reasoning import ReasoningConfidence, RecommendedAction

_SEVERITY_ACTION_MAP: dict[SeverityLevel, tuple[RecommendedAction, ReasoningConfidence, float]] = {
    SeverityLevel.LOW: (RecommendedAction.MONITOR, ReasoningConfidence.HIGH, 0.85),
    SeverityLevel.MEDIUM: (RecommendedAction.REQUEST_REVIEW, ReasoningConfidence.MEDIUM, 0.65),
    SeverityLevel.HIGH: (RecommendedAction.NOTIFY_STAFF, ReasoningConfidence.MEDIUM, 0.55),
    SeverityLevel.CRITICAL: (RecommendedAction.ESCALATE, ReasoningConfidence.LOW, 0.35),
}


class MockLLMReasoner(Reasoner):
    """Deterministic structured-event reasoner — no external LLM dependencies."""

    def __init__(self, model_id: str = "mock-llm-reasoner") -> None:
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    def reason(self, reasoning_input: LocalReasoningInput) -> LocalReasoningOutput:
        validate_reasoning_payload(reasoning_input.model_dump(mode="json"))
        # Prompt is built to mirror future LLM integration; mock uses structured fields directly.
        _ = build_structured_prompt(reasoning_input)

        anchor = reasoning_input.anchor_event
        legacy_severity = anchor.metadata.get("legacy_severity")
        if legacy_severity == "info":
            action = RecommendedAction.NO_ACTION
            confidence_band = ReasoningConfidence.HIGH
            confidence_value = 0.9
        else:
            action, confidence_band, confidence_value = _SEVERITY_ACTION_MAP.get(
                anchor.severity,
                (RecommendedAction.REQUEST_REVIEW, ReasoningConfidence.MEDIUM, 0.5),
            )

        cited_event_ids = tuple(
            sorted(
                {anchor.event_id, *(event.event_id for event in reasoning_input.context_events)},
                key=str,
            )
        )

        route_fragment = ""
        graph = reasoning_input.graph_context
        if graph is not None and graph.affected_route_ids:
            routes = ", ".join(graph.affected_route_ids)
            route_fragment = f" Affected routes: {routes}."

        constraint_fragment = ""
        if reasoning_input.safety_constraints:
            constraint_fragment = (
                f" Active constraint: {reasoning_input.safety_constraints[0].description}."
            )

        protocol_fragment = ""
        if reasoning_input.available_protocols:
            protocol_fragment = (
                f" Protocol reference: {reasoning_input.available_protocols[0].protocol_name}."
            )

        recommendation = (
            f"{action.value.replace('_', ' ').title()} for zone {anchor.zone_id} "
            f"following {anchor.event_type.value}."
        )
        rationale = (
            f"Structured anchor event {anchor.event_id} reports {anchor.event_type.value} "
            f"in zone {anchor.zone_id} at severity {anchor.severity.value}.{route_fragment}"
            f"{constraint_fragment}{protocol_fragment} "
            f"Assessment uses {len(cited_event_ids)} cited semantic event(s) only; "
            "no raw media or identity data was consumed."
        )

        uncertainty_notes: list[str] = []
        if len(reasoning_input.context_events) < 2:
            uncertainty_notes.append("Sparse temporal context window.")
        if anchor.confidence < 0.5:
            uncertainty_notes.append("Anchor event confidence is below 0.5.")
        if reasoning_input.graph_context is None:
            uncertainty_notes.append("No temporal graph context was supplied.")

        required_human_review = requires_human_review_for_severity(
            anchor.severity.value
        ) or anchor.severity in {SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL}

        return LocalReasoningOutput(
            request_id=reasoning_input.request_id,
            recommendation=recommendation,
            rationale=rationale,
            confidence=confidence_value,
            required_human_review=required_human_review,
            uncertainty_notes=(
                " ".join(uncertainty_notes)
                if uncertainty_notes
                else "No significant uncertainty noted."
            ),
            cited_event_ids=cited_event_ids,
            recommended_action=action,
            confidence_band=confidence_band,
            model_id=self._model_id,
        )
