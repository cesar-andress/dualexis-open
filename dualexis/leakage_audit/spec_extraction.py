"""Extract variables, thresholds, and logic from E2 simulator components."""

from __future__ import annotations

import ast
from pathlib import Path

from dualexis.simulation import world_dynamics
from dualexis.simulation.gt_rules import load_ground_truth_rules
from dualexis.simulation.scenario import ScenarioId
from dualexis.leakage_audit.models import ComponentSpec, LogicPredicate, ThresholdPredicate

CANONICAL_VARIABLES = frozenset(
    {
        "zone_density",
        "zone_activity",
        "zone_audio",
        "exit_throughput",
        "tick",
        "elapsed_seconds",
    }
)

# world_dynamics: implicit tick-ramp thresholds (derived from source literals).
_WORLD_DYNAMICS_THRESHOLDS: tuple[ThresholdPredicate, ...] = (
    ThresholdPredicate(
        metric="zone_density",
        zone="*",
        operator="ramp",
        value=0.25,
        component="world_dynamics",
        label="normal_flow baseline density",
    ),
    ThresholdPredicate(
        metric="zone_density",
        zone="cafeteria",
        operator="ramp",
        value=0.06,
        scenario_id="crowd_acceleration",
        component="world_dynamics",
        label="crowd density ramp per tick",
    ),
    ThresholdPredicate(
        metric="exit_throughput",
        zone="exit-main",
        operator="decay",
        value=0.12,
        scenario_id="exit_blockage",
        component="world_dynamics",
        label="exit throughput decay per tick",
    ),
    ThresholdPredicate(
        metric="zone_audio",
        zone="hallway-a",
        operator="ramp",
        value=0.07,
        scenario_id="audio_stress_signal",
        component="world_dynamics",
        label="audio stress ramp",
    ),
    ThresholdPredicate(
        metric="zone_audio",
        zone="cafeteria",
        operator="ramp",
        value=0.08,
        scenario_id="multimodal_conflict",
        component="world_dynamics",
        label="cafeteria audio ramp",
    ),
    ThresholdPredicate(
        metric="zone_density",
        zone="*",
        operator="ramp",
        value=0.07,
        scenario_id="evacuation_recommendation",
        component="world_dynamics",
        label="evacuation density ramp",
    ),
)

_WORLD_DYNAMICS_LOGIC: tuple[LogicPredicate, ...] = tuple(
    LogicPredicate(
        predicate_id=f"wd-{scenario.value}",
        scenario_id=scenario.value,
        component="world_dynamics",
        expression=f"advance_world_state branch:{scenario.value}",
    )
    for scenario in ScenarioId
)


def _extract_event_generator_thresholds() -> tuple[ThresholdPredicate, ...]:
    """Procedural thresholds for decoupled metric-heuristic emission profiles."""
    from dualexis.simulation.emission_profiles import load_emission_profile

    thresholds: list[ThresholdPredicate] = []
    for scenario in ScenarioId:
        doc = load_emission_profile(scenario)
        for rule in doc.emit_rules:
            for cond in rule.conditions:
                thresholds.append(
                    ThresholdPredicate(
                        metric=cond.metric,
                        zone=cond.zone if cond.zone != "*" else rule.zone_id,
                        operator=cond.op.value,
                        value=cond.value,
                        scenario_id=scenario.value,
                        component="metric_heuristic_emitter",
                        label=rule.semantic_label,
                    )
                )
    return tuple(thresholds)


def _extract_event_generator_logic() -> tuple[LogicPredicate, ...]:
    return tuple(
        LogicPredicate(
            predicate_id=f"eg-{scenario.value}",
            scenario_id=scenario.value,
            component="metric_heuristic_emitter",
            expression=f"emit_metric_heuristic_events scenario=={scenario.value}",
        )
        for scenario in ScenarioId
    )


def extract_ground_truth_rules_spec() -> ComponentSpec:
    thresholds: list[ThresholdPredicate] = []
    logic: list[LogicPredicate] = []
    for scenario in ScenarioId:
        doc = load_ground_truth_rules(scenario)
        for rule in doc.label_rules:
            expr_parts = [f"min_tick>={rule.min_tick}", f"zone={rule.zone_id}"]
            for cond in rule.conditions:
                thresholds.append(
                    ThresholdPredicate(
                        metric=cond.metric,
                        zone=cond.zone if cond.zone != "*" else rule.zone_id,
                        operator=cond.op.value,
                        value=cond.value,
                        scenario_id=scenario.value,
                        component="ground_truth_rules",
                        label=rule.semantic_label,
                    )
                )
                expr_parts.append(f"{cond.metric}@{cond.zone} {cond.op.value} {cond.value}")
            logic.append(
                LogicPredicate(
                    predicate_id=f"gt-{scenario.value}-{rule.semantic_label}",
                    scenario_id=scenario.value,
                    component="ground_truth_rules",
                    expression=" AND ".join(expr_parts),
                )
            )
    return ComponentSpec(
        component_id="ground_truth_rules",
        variables=tuple(sorted(CANONICAL_VARIABLES)),
        thresholds=tuple(thresholds),
        logic_predicates=tuple(logic),
    )


def extract_world_dynamics_spec() -> ComponentSpec:
    return ComponentSpec(
        component_id="world_dynamics",
        variables=tuple(sorted(CANONICAL_VARIABLES)),
        thresholds=_WORLD_DYNAMICS_THRESHOLDS,
        logic_predicates=_WORLD_DYNAMICS_LOGIC,
    )


def extract_event_generator_spec() -> ComponentSpec:
    return ComponentSpec(
        component_id="metric_heuristic_emitter",
        variables=tuple(sorted(CANONICAL_VARIABLES)),
        thresholds=_extract_event_generator_thresholds(),
        logic_predicates=_extract_event_generator_logic(),
    )


def extract_all_specs() -> tuple[ComponentSpec, ComponentSpec, ComponentSpec]:
    return (
        extract_world_dynamics_spec(),
        extract_event_generator_spec(),
        extract_ground_truth_rules_spec(),
    )


def independent_labeler_imports_event_generator() -> bool:
    """AST check: procedural coupling via imports."""
    path = Path(__file__).resolve().parents[1] / "simulation" / "independent_labeler.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "event_generator" in node.module:
            return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "event_generator" in alias.name:
                    return True
    return False


__all__ = [
    "CANONICAL_VARIABLES",
    "extract_all_specs",
    "extract_event_generator_spec",
    "extract_ground_truth_rules_spec",
    "extract_world_dynamics_spec",
    "independent_labeler_imports_event_generator",
]
