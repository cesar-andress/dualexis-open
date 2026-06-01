"""End-to-end pipeline service interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from dualexis.pipeline.models import PipelineInput, PipelineOutput
from dualexis.simulation.runner import SimulationResult


class PipelineService(ABC):
    """Orchestrates L1--L6 modules into a single advisory pipeline."""

    @abstractmethod
    async def run(
        self,
        inputs: Sequence[PipelineInput],
        *,
        scenario_name: str | None = None,
        seed: int | None = None,
        simulation: SimulationResult | None = None,
    ) -> PipelineOutput:
        """Execute the pipeline on synthetic inputs and return structured outputs."""
