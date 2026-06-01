"""Placeholder reasoning engine — delegates to deterministic MockLLMReasoner."""

from __future__ import annotations

from dualexis.core.interfaces import ReasoningEngine
from dualexis.local_reasoning.mock_llm import MockLLMReasoner
from dualexis.local_reasoning.service import (
    reasoning_input_from_request,
    reasoning_response_from_output,
)
from dualexis.schemas.reasoning import ReasoningRequest, ReasoningResponse


class PlaceholderReasoningEngine(ReasoningEngine):
    """Deterministic reasoning placeholder backed by ``MockLLMReasoner``."""

    def __init__(self, model_id: str = "mock-llm-reasoner") -> None:
        self._reasoner = MockLLMReasoner(model_id=model_id)
        self._available = True

    async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        reasoning_input = reasoning_input_from_request(request)
        output = self._reasoner.reason(reasoning_input)
        return reasoning_response_from_output(
            output,
            anchor_event_id=reasoning_input.anchor_event.event_id,
        )

    def is_available(self) -> bool:
        return self._available
