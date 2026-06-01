"""L5 Local Reasoning Layer — data models.

Maps to DUALEXIS Framework Layer 5 (Local Reasoning Layer).
Structured-event-only copilot I/O with explicit privacy boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.orchestration.models import HIGH_RISK_SEVERITIES
from dualexis.privacy_runtime.models import is_forbidden_field
from dualexis.schemas.reasoning import (
    ReasoningConfidence,
    ReasoningRequest,
    ReasoningResponse,
    RecommendedAction,
)
from dualexis.semantic_events.models import SemanticEvent
from dualexis.temporal_graph.models import GraphContext

# Additional image-oriented keys rejected at the L5 trust boundary (TB4).
REASONING_FORBIDDEN_IMAGE_FIELDS: frozenset[str] = frozenset(
    {
        "image",
        "image_data",
        "image_bytes",
        "jpeg",
        "png",
        "png_bytes",
        "photo",
        "raw_image",
        "screenshot",
    }
)


@dataclass(frozen=True)
class LayerMetadata:
    """Static descriptor for the local reasoning framework layer."""

    layer_id: str = "L5"
    name: str = "local_reasoning"
    processes_events_only: bool = True


@dataclass(frozen=True)
class CopilotConfig:
    """Configuration for a local reasoning backend."""

    model_id: str = "mock-llm-reasoner"
    max_context_events: int = 32
    allow_raw_media_prompts: bool = False


class SafetyConstraint(BaseModel):
    """Active safety constraint supplied to the reasoner."""

    model_config = ConfigDict(frozen=True)

    constraint_id: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=512)
    severity: str = Field(default="medium", min_length=1, max_length=32)


class AvailableProtocol(BaseModel):
    """Closed-vocabulary operational protocol available to the reasoner."""

    model_config = ConfigDict(frozen=True)

    protocol_id: str = Field(min_length=1, max_length=64)
    protocol_name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)


class LocalReasoningInput(BaseModel):
    """Privacy-bounded input for local reasoning (TB4).

    Permitted: semantic events, temporal graph context, safety constraints,
    and available protocols only.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1, max_length=128)
    anchor_event: SemanticEvent
    context_events: tuple[SemanticEvent, ...] = Field(default_factory=tuple)
    graph_context: GraphContext | None = None
    safety_constraints: tuple[SafetyConstraint, ...] = Field(default_factory=tuple)
    available_protocols: tuple[AvailableProtocol, ...] = Field(default_factory=tuple)


class LocalReasoningOutput(BaseModel):
    """Structured advisory output from local reasoning."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1, max_length=128)
    recommendation: str = Field(min_length=1, max_length=1024)
    rationale: str = Field(min_length=1, max_length=4096)
    confidence: float = Field(ge=0.0, le=1.0)
    required_human_review: bool
    uncertainty_notes: str = Field(min_length=1, max_length=2048)
    cited_event_ids: tuple[UUID, ...] = Field(min_length=1)
    recommended_action: RecommendedAction
    confidence_band: ReasoningConfidence
    model_id: str = Field(default="mock-llm-reasoner")


def _normalize_key(key: str) -> str:
    return key.lower().replace("-", "_")


def _is_forbidden_reasoning_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if is_forbidden_field(key):
        return True
    return normalized in REASONING_FORBIDDEN_IMAGE_FIELDS


def validate_reasoning_payload(payload: Any, *, path: str = "root") -> None:
    """Fail-closed scan for forbidden media, biometric, and identity fields.

    Raises ``PrivacyViolationError`` when raw media, images, biometrics, or
    personal identity fields appear anywhere in the serialized reasoning input.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_str = str(key)
            if _is_forbidden_reasoning_key(key_str):
                msg = (
                    f"Forbidden reasoning input field '{key_str}' at {path} "
                    "(raw media, images, biometrics, and identities are prohibited)"
                )
                raise PrivacyViolationError(msg)
            validate_reasoning_payload(value, path=f"{path}.{key_str}")
        return

    if isinstance(payload, list):
        for index, item in enumerate(payload):
            validate_reasoning_payload(item, path=f"{path}[{index}]")
        return

    if isinstance(payload, tuple):
        for index, item in enumerate(payload):
            validate_reasoning_payload(item, path=f"{path}[{index}]")


def requires_human_review_for_severity(severity_value: str) -> bool:
    """Return whether a severity tier mandates human review."""
    return severity_value in HIGH_RISK_SEVERITIES


LOCAL_REASONING_LAYER = LayerMetadata()

__all__ = [
    "LOCAL_REASONING_LAYER",
    "REASONING_FORBIDDEN_IMAGE_FIELDS",
    "AvailableProtocol",
    "CopilotConfig",
    "LayerMetadata",
    "LocalReasoningInput",
    "LocalReasoningOutput",
    "ReasoningConfidence",
    "ReasoningRequest",
    "ReasoningResponse",
    "RecommendedAction",
    "SafetyConstraint",
    "requires_human_review_for_severity",
    "validate_reasoning_payload",
]
