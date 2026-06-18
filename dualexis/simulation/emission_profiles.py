"""Load and evaluate decoupled simulator emission profiles.

Emission profiles live under ``experiments/simulator/emission_profiles/`` and are
intentionally separate from ground-truth rule YAML under ``experiments/ground_truth/rules/``.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from dualexis.semantic_events.models import EventType
from dualexis.simulation.scenario import ScenarioId


class MetricOp(StrEnum):
    GTE = "gte"
    LT = "lt"


class EmissionCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(
        description="zone_density | zone_activity | zone_audio | exit_throughput"
    )
    zone: str = Field(description="Zone id or '*' for all zones")
    op: MetricOp
    value: float


class EmissionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    semantic_label: str = Field(min_length=1, max_length=128)
    zone_id: str = Field(min_length=1, max_length=64)
    expected_event_type: EventType
    min_tick: int = Field(default=0, ge=0)
    max_zones_per_tick: int | None = Field(default=None, ge=1)
    conditions: tuple[EmissionCondition, ...] = Field(min_length=1)
    miss_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    spurious_probability: float = Field(default=0.0, ge=0.0, le=1.0)


class EmissionProfileDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: ScenarioId
    version: str = "emit_profiles_v1"
    description: str = ""
    emit_rules: tuple[EmissionRule, ...] = Field(min_length=1)


def default_profiles_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "experiments" / "simulator" / "emission_profiles"


def profile_path_for(scenario_id: ScenarioId, *, base_dir: Path | None = None) -> Path:
    root = base_dir or default_profiles_dir()
    return root / f"{scenario_id.value}.yaml"


def load_emission_profile(
    scenario_id: ScenarioId,
    *,
    base_dir: Path | None = None,
) -> EmissionProfileDocument:
    path = profile_path_for(scenario_id, base_dir=base_dir)
    if not path.is_file():
        msg = f"Missing emission profile file: {path}"
        raise FileNotFoundError(msg)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc = EmissionProfileDocument.model_validate(raw)
    if doc.scenario_id != scenario_id:
        msg = f"Profile scenario mismatch in {path}: {doc.scenario_id} != {scenario_id}"
        raise ValueError(msg)
    return doc


def _metric_value(
    metric: str,
    zone_id: str,
    *,
    zone_density: dict[str, float],
    zone_activity: dict[str, float],
    zone_audio: dict[str, float],
    exit_throughput: dict[str, float],
) -> float | None:
    if metric == "zone_density":
        return zone_density.get(zone_id)
    if metric == "zone_activity":
        return zone_activity.get(zone_id)
    if metric == "zone_audio":
        return zone_audio.get(zone_id)
    if metric == "exit_throughput":
        return exit_throughput.get(zone_id)
    return None


def _condition_holds(condition: EmissionCondition, value: float | None) -> bool:
    if value is None:
        return False
    if condition.op == MetricOp.GTE:
        return value >= condition.value
    if condition.op == MetricOp.LT:
        return value < condition.value
    return False


def _condition_satisfied(
    condition: EmissionCondition,
    *,
    label_zone_id: str,
    zone_density: dict[str, float],
    zone_activity: dict[str, float],
    zone_audio: dict[str, float],
    exit_throughput: dict[str, float],
) -> bool:
    target_zone = condition.zone if condition.zone != "*" else label_zone_id
    value = _metric_value(
        condition.metric,
        target_zone,
        zone_density=zone_density,
        zone_activity=zone_activity,
        zone_audio=zone_audio,
        exit_throughput=exit_throughput,
    )
    return _condition_holds(condition, value)


def emission_rule_matches_tick(
    rule: EmissionRule,
    *,
    tick: int,
    zone_density: dict[str, float],
    zone_activity: dict[str, float],
    zone_audio: dict[str, float],
    exit_throughput: dict[str, float],
) -> list[str]:
    """Return zone ids for which *rule* fires on this tick (empty if none)."""
    if tick < rule.min_tick:
        return []

    if rule.zone_id == "*":
        candidate_zones = sorted(zone_density)
    else:
        candidate_zones = [rule.zone_id]

    matched: list[str] = []
    for label_zone in candidate_zones:
        if all(
            _condition_satisfied(
                condition,
                label_zone_id=label_zone,
                zone_density=zone_density,
                zone_activity=zone_activity,
                zone_audio=zone_audio,
                exit_throughput=exit_throughput,
            )
            for condition in rule.conditions
        ):
            matched.append(label_zone)

    if rule.max_zones_per_tick is not None:
        return matched[: rule.max_zones_per_tick]
    return matched


__all__ = [
    "EmissionCondition",
    "EmissionProfileDocument",
    "EmissionRule",
    "MetricOp",
    "default_profiles_dir",
    "emission_rule_matches_tick",
    "load_emission_profile",
    "profile_path_for",
]
