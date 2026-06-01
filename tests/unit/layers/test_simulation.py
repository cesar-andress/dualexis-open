"""Unit tests for simulation layer."""

from __future__ import annotations

import pytest

from dualexis.simulation import DefaultSimulationService, SimulationScenario


@pytest.mark.unit
def test_simulation_generates_ephemeral_frames() -> None:
    service = DefaultSimulationService()
    batch = service.generate_batch(
        SimulationScenario.MULTIMODAL_CORRELATED,
        node_id="sim-001",
        zone_id="cafeteria",
    )
    assert len(batch.frames) == 3
    assert all(f.payload_ref is None for f in batch.frames)
