"""L5 Local Reasoning Layer — service interfaces.

Maps to DUALEXIS Framework Layer 5 (Local Reasoning Layer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dualexis.local_reasoning.models import (
    LocalReasoningInput,
    LocalReasoningOutput,
    ReasoningRequest,
    ReasoningResponse,
)


class Reasoner(ABC):
    """Structured-event reasoner backend (local LLM or deterministic mock)."""

    @abstractmethod
    def reason(self, reasoning_input: LocalReasoningInput) -> LocalReasoningOutput:
        """Produce advisory reasoning output from privacy-bounded structured input."""


class LocalReasoningService(ABC):
    """Safety orchestration copilot over structured event subgraphs only."""

    @abstractmethod
    async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        """Produce advisory reasoning output from a legacy reasoning request."""

    @abstractmethod
    async def reason_structured(
        self,
        reasoning_input: LocalReasoningInput,
    ) -> LocalReasoningOutput:
        """Produce advisory reasoning output from structured L5 input."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the local reasoning backend is ready."""
