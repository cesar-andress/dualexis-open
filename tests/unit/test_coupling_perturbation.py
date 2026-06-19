"""Unit tests for coupling perturbation utilities."""

from __future__ import annotations

from dataclasses import replace

from dualexis.simulation.coupling_perturbation import (
    CouplingChannel,
    CouplingPerturbationConfig,
    apply_coupling_perturbation,
    apply_noise_injection,
    apply_temporal_desync,
    apply_zone_permutation,
    retained_coupling_proxy,
    zone_value_multiset,
)
from dualexis.simulation.world import build_default_world, initial_world_state


def _sample_state(tick: int = 3):
    graph = build_default_world()
    state = initial_world_state(graph)
    return replace(
        state,
        tick=tick,
        zone_density={"hallway-a": 0.2, "cafeteria": 0.5, "exit-lobby": 0.7},
        zone_activity={"hallway-a": 0.1, "cafeteria": 0.4, "exit-lobby": 0.6},
        zone_audio_stress={"hallway-a": 0.3, "cafeteria": 0.2, "exit-lobby": 0.8},
    )


def test_lambda_zero_reproduces_clean_emitter_input() -> None:
    clean = _sample_state()
    for channel in CouplingChannel:
        config = CouplingPerturbationConfig(channel=channel, lambda_=0.0, seed=7)
        perturbed = apply_coupling_perturbation(clean, config=config, history=(clean,))
        assert perturbed.zone_density == clean.zone_density
        assert perturbed.zone_activity == clean.zone_activity
        assert retained_coupling_proxy(clean, perturbed) == 1.0


def test_zone_permutation_preserves_marginals_but_changes_assignment() -> None:
    clean = _sample_state()
    config = CouplingPerturbationConfig(
        channel=CouplingChannel.ZONE_PERMUTATION,
        lambda_=1.0,
        seed=11,
    )
    perturbed = apply_zone_permutation(clean, config=config)
    assert zone_value_multiset(clean) == zone_value_multiset(perturbed)
    assert perturbed.zone_density != clean.zone_density


def test_temporal_desync_uses_lagged_values() -> None:
    earlier = _sample_state(tick=1)
    later = _sample_state(tick=4)
    config = CouplingPerturbationConfig(
        channel=CouplingChannel.TEMPORAL_DESYNC,
        lambda_=1.0,
        seed=3,
        max_temporal_lag=4,
    )
    perturbed = apply_temporal_desync(later, config=config, history=(earlier, earlier, later))
    assert perturbed.zone_density == earlier.zone_density
    assert perturbed.tick == later.tick


def test_noise_injection_changes_values_within_bounds() -> None:
    clean = _sample_state()
    config = CouplingPerturbationConfig(
        channel=CouplingChannel.NOISE_INJECTION,
        lambda_=1.0,
        seed=5,
        noise_scale=0.35,
    )
    perturbed = apply_noise_injection(clean, config=config)
    assert perturbed.zone_density != clean.zone_density
    assert all(0.0 <= value <= 1.0 for value in perturbed.zone_density.values())


def test_coupling_proxy_decreases_under_full_zone_permutation() -> None:
    clean = _sample_state()
    config = CouplingPerturbationConfig(
        channel=CouplingChannel.ZONE_PERMUTATION,
        lambda_=1.0,
        seed=19,
    )
    perturbed = apply_zone_permutation(clean, config=config)
    assert retained_coupling_proxy(clean, perturbed) < 1.0
