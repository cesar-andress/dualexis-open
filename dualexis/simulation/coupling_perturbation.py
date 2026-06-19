"""Coupling-controlled perturbations for emitter-visible simulator variables.

The ground-truth oracle always consumes clean world state; perturbations apply only
to the metric-heuristic emitter view. Diagnostic experiment only.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, replace
from enum import StrEnum

from dualexis.simulation.world import WorldState

DEFAULT_LAMBDAS: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
DEFAULT_MAX_TEMPORAL_LAG: int = 4
DEFAULT_NOISE_SCALE: float = 0.35


class CouplingChannel(StrEnum):
    """Perturbation channels destroying shared input structure for the emitter."""

    ZONE_PERMUTATION = "zone_permutation"
    TEMPORAL_DESYNC = "temporal_desync"
    NOISE_INJECTION = "noise_injection"


@dataclass(frozen=True)
class CouplingPerturbationConfig:
    channel: CouplingChannel
    lambda_: float
    seed: int
    max_temporal_lag: int = DEFAULT_MAX_TEMPORAL_LAG
    noise_scale: float = DEFAULT_NOISE_SCALE


def _unit_uniform(token: str) -> float:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _zone_ids(state: WorldState) -> tuple[str, ...]:
    return tuple(sorted(state.zone_density.keys()))


def _permute_zone_dict(values: dict[str, float], permutation: dict[str, str]) -> dict[str, float]:
    return {zone: values[source] for zone, source in permutation.items()}


def _build_zone_permutation(
    zones: tuple[str, ...],
    *,
    seed: int,
    tick: int,
    channel: CouplingChannel,
) -> dict[str, str]:
    order = list(zones)
    rng = random.Random(f"{seed}:{tick}:{channel.value}:perm")
    rng.shuffle(order)
    return dict(zip(zones, order, strict=True))


def _mixed_zone_permutation(
    zones: tuple[str, ...],
    *,
    seed: int,
    tick: int,
    channel: CouplingChannel,
    lambda_: float,
) -> dict[str, str]:
    target = _build_zone_permutation(zones, seed=seed, tick=tick, channel=channel)
    mapping: dict[str, str] = {}
    for zone in zones:
        token = f"{seed}:{tick}:{channel.value}:{zone}:{lambda_}"
        if _unit_uniform(token) < lambda_:
            mapping[zone] = target[zone]
        else:
            mapping[zone] = zone
    return mapping


def apply_zone_permutation(
    clean: WorldState,
    *,
    config: CouplingPerturbationConfig,
) -> WorldState:
    """Shuffle zone identities for emitter-visible metrics; preserve value multiset."""
    if config.lambda_ <= 0.0:
        return clean
    zones = _zone_ids(clean)
    mapping = _mixed_zone_permutation(
        zones,
        seed=config.seed,
        tick=clean.tick,
        channel=config.channel,
        lambda_=min(1.0, config.lambda_),
    )
    return replace(
        clean,
        zone_density=_permute_zone_dict(clean.zone_density, mapping),
        zone_activity=_permute_zone_dict(clean.zone_activity, mapping),
        zone_audio_stress=_permute_zone_dict(clean.zone_audio_stress, mapping),
    )


def apply_temporal_desync(
    clean: WorldState,
    *,
    config: CouplingPerturbationConfig,
    history: tuple[WorldState, ...],
) -> WorldState:
    """Feed lagged clean metrics to the emitter; GT uses the current tick."""
    if config.lambda_ <= 0.0 or not history:
        return clean
    lag = int(round(min(1.0, config.lambda_) * config.max_temporal_lag))
    if lag <= 0:
        return clean
    source = history[-lag] if lag <= len(history) else history[0]
    return replace(
        clean,
        zone_density=dict(source.zone_density),
        zone_activity=dict(source.zone_activity),
        zone_audio_stress=dict(source.zone_audio_stress),
        exit_throughput=dict(source.exit_throughput),
    )


def _noisy_value(
    value: float,
    *,
    seed: int,
    tick: int,
    zone: str,
    metric: str,
    lambda_: float,
    noise_scale: float,
) -> float:
    token = f"{seed}:{tick}:{zone}:{metric}:noise"
    z = (_unit_uniform(token) * 2.0 - 1.0) * 2.0
    perturbed = value + lambda_ * noise_scale * z
    return max(0.0, min(1.0, perturbed))


def apply_noise_injection(
    clean: WorldState,
    *,
    config: CouplingPerturbationConfig,
) -> WorldState:
    """Add scaled noise to emitter-visible variables; GT remains clean."""
    if config.lambda_ <= 0.0:
        return clean
    lam = min(1.0, config.lambda_)
    density = {
        zone: _noisy_value(
            value,
            seed=config.seed,
            tick=clean.tick,
            zone=zone,
            metric="density",
            lambda_=lam,
            noise_scale=config.noise_scale,
        )
        for zone, value in clean.zone_density.items()
    }
    activity = {
        zone: _noisy_value(
            value,
            seed=config.seed,
            tick=clean.tick,
            zone=zone,
            metric="activity",
            lambda_=lam,
            noise_scale=config.noise_scale,
        )
        for zone, value in clean.zone_activity.items()
    }
    audio = {
        zone: _noisy_value(
            value,
            seed=config.seed,
            tick=clean.tick,
            zone=zone,
            metric="audio",
            lambda_=lam,
            noise_scale=config.noise_scale,
        )
        for zone, value in clean.zone_audio_stress.items()
    }
    throughput = {
        exit_id: _noisy_value(
            value,
            seed=config.seed,
            tick=clean.tick,
            zone=exit_id,
            metric="throughput",
            lambda_=lam,
            noise_scale=config.noise_scale,
        )
        for exit_id, value in clean.exit_throughput.items()
    }
    return replace(
        clean,
        zone_density=density,
        zone_activity=activity,
        zone_audio_stress=audio,
        exit_throughput=throughput,
    )


def apply_coupling_perturbation(
    clean: WorldState,
    *,
    config: CouplingPerturbationConfig,
    history: tuple[WorldState, ...] = (),
) -> WorldState:
    """Return emitter-visible world state under the configured coupling channel."""
    if config.channel == CouplingChannel.ZONE_PERMUTATION:
        return apply_zone_permutation(clean, config=config)
    if config.channel == CouplingChannel.TEMPORAL_DESYNC:
        return apply_temporal_desync(clean, config=config, history=history)
    if config.channel == CouplingChannel.NOISE_INJECTION:
        return apply_noise_injection(clean, config=config)
    msg = f"Unknown coupling channel: {config.channel}"
    raise ValueError(msg)


def _flatten_zone_metrics(state: WorldState) -> list[float]:
    zones = _zone_ids(state)
    values: list[float] = []
    for zone in zones:
        values.extend(
            [
                state.zone_density.get(zone, 0.0),
                state.zone_activity.get(zone, 0.0),
                state.zone_audio_stress.get(zone, 0.0),
            ]
        )
    return values


def pearson_correlation(left: list[float], right: list[float]) -> float:
    """Pearson correlation; returns 0.0 when undefined."""
    if len(left) != len(right) or not left:
        return 0.0
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    num = sum((a - mean_l) * (b - mean_r) for a, b in zip(left, right, strict=True))
    den_l = math.sqrt(sum((a - mean_l) ** 2 for a in left))
    den_r = math.sqrt(sum((b - mean_r) ** 2 for b in right))
    if den_l == 0.0 or den_r == 0.0:
        return 1.0 if left == right else 0.0
    return max(-1.0, min(1.0, num / (den_l * den_r)))


def retained_coupling_proxy(clean: WorldState, perturbed: WorldState) -> float:
    """Normalized similarity between clean and emitter-visible metric vectors."""
    return round(pearson_correlation(_flatten_zone_metrics(clean), _flatten_zone_metrics(perturbed)), 4)


def zone_value_multiset(state: WorldState) -> tuple[float, ...]:
    """Sorted multiset of zone-level metric values (marginal preservation check)."""
    values: list[float] = []
    for metric in (
        state.zone_density,
        state.zone_activity,
        state.zone_audio_stress,
    ):
        values.extend(metric.values())
    return tuple(sorted(values))


__all__ = [
    "DEFAULT_LAMBDAS",
    "DEFAULT_MAX_TEMPORAL_LAG",
    "DEFAULT_NOISE_SCALE",
    "CouplingChannel",
    "CouplingPerturbationConfig",
    "apply_coupling_perturbation",
    "apply_noise_injection",
    "apply_temporal_desync",
    "apply_zone_permutation",
    "pearson_correlation",
    "retained_coupling_proxy",
    "zone_value_multiset",
]
