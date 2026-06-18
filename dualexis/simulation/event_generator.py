"""Synthetic semantic event generator for simulation.

Default path uses decoupled metric-heuristic emission profiles. Shared-spec
rule-driven emission is available for regression checks only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.emission_mode import EmissionMode
from dualexis.simulation.metric_heuristic_emitter import emit_metric_heuristic_events
from dualexis.simulation.rule_driven_emitter import emit_rule_driven_events
from dualexis.simulation.scenario import ScenarioId
from dualexis.simulation.world import WorldState


class SyntheticEventGenerator:
    """Generates domain ``SemanticEvent`` objects from anonymous world metrics."""

    def __init__(
        self,
        *,
        node_id: str = "sim-edge-001",
        start_time: datetime | None = None,
        emission_mode: EmissionMode = EmissionMode.DECOUPLED,
        seed: int = 42,
    ) -> None:
        self._node_id = node_id
        self._start_time = start_time or datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        self._emission_mode = emission_mode
        self._seed = seed

    @property
    def emission_mode(self) -> EmissionMode:
        return self._emission_mode

    def timestamp_for_tick(self, tick: int, *, tick_seconds: float) -> datetime:
        from datetime import timedelta

        return self._start_time + timedelta(seconds=tick * tick_seconds)

    def generate_events(
        self,
        state: WorldState,
        *,
        scenario_id: ScenarioId,
        tick_seconds: float,
    ) -> tuple[SemanticEvent, ...]:
        """Emit zone-level semantic events for the current tick."""
        if self._emission_mode == EmissionMode.SHARED_SPEC:
            return emit_rule_driven_events(
                state,
                scenario_id=scenario_id,
                tick_seconds=tick_seconds,
                node_id=self._node_id,
                start_time=self._start_time,
            )
        return emit_metric_heuristic_events(
            state,
            scenario_id=scenario_id,
            seed=self._seed,
            tick_seconds=tick_seconds,
            node_id=self._node_id,
            start_time=self._start_time,
        )


__all__ = ["SyntheticEventGenerator"]
