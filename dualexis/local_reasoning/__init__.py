"""L5 Local Reasoning Layer — structured-event copilot (Framework Layer 5)."""

from dualexis.local_reasoning.interfaces import LocalReasoningService, Reasoner
from dualexis.local_reasoning.mock_llm import MockLLMReasoner
from dualexis.local_reasoning.models import (
    LOCAL_REASONING_LAYER,
    AvailableProtocol,
    CopilotConfig,
    LayerMetadata,
    LocalReasoningInput,
    LocalReasoningOutput,
    ReasoningRequest,
    ReasoningResponse,
    SafetyConstraint,
    validate_reasoning_payload,
)
from dualexis.local_reasoning.prompt_templates import build_structured_prompt
from dualexis.local_reasoning.service import (
    DefaultLocalReasoningService,
    PlaceholderLocalReasoningService,
    reasoning_input_from_request,
    reasoning_response_from_output,
)

__all__ = [
    "LOCAL_REASONING_LAYER",
    "AvailableProtocol",
    "CopilotConfig",
    "DefaultLocalReasoningService",
    "LayerMetadata",
    "LocalReasoningInput",
    "LocalReasoningOutput",
    "LocalReasoningService",
    "MockLLMReasoner",
    "PlaceholderLocalReasoningService",
    "Reasoner",
    "ReasoningRequest",
    "ReasoningResponse",
    "SafetyConstraint",
    "build_structured_prompt",
    "reasoning_input_from_request",
    "reasoning_response_from_output",
    "validate_reasoning_payload",
]
