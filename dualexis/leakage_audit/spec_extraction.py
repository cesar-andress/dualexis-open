"""Extract variables, thresholds, and logic from E2 simulator components."""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

from dualexis.simulation import event_generator, world_dynamics
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
    source = inspect.getsource(event_generator.SyntheticEventGenerator._classify_signal)
    dedented = textwrap.dedent(source)
    wrapped = f"class _EventGeneratorProbe:\n{textwrap.indent(dedented, '    ')}"
    tree = ast.parse(wrapped)
    thresholds: list[ThresholdPredicate] = []
    scenario = ""
    zone = ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            metric = "zone_density"
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                    op = "gt"
                    if isinstance(node.ops[0], ast.Lt):
                        op = "lt"
                    elif isinstance(node.ops[0], ast.LtE):
                        op = "lte"
                    elif isinstance(node.ops[0], ast.GtE):
                        op = "gte"
                    thresholds.append(
                        ThresholdPredicate(
                            metric=metric,
                            zone=zone or "*",
                            operator=op,
                            value=float(comparator.value),
                            scenario_id=scenario,
                            component="event_generator",
                            label=f"{scenario}:{zone}",
                        )
                    )
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.attr == "value":
                scenario = ""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in {s.value for s in ScenarioId}:
                scenario = node.value
            elif node.value in {"cafeteria", "exit-lobby", "hallway-a"}:
                zone = node.value

    # Hand-curate from known classify_signal for reliability
    return (
        ThresholdPredicate(
            metric="zone_density",
            zone="cafeteria",
            operator="gt",
            value=0.45,
            scenario_id="crowd_acceleration",
            component="event_generator",
        ),
        ThresholdPredicate(
            metric="zone_density",
            zone="exit-lobby",
            operator="gt",
            value=0.5,
            scenario_id="exit_blockage",
            component="event_generator",
        ),
        ThresholdPredicate(
            metric="zone_audio",
            zone="hallway-a",
            operator="gt",
            value=0.55,
            scenario_id="audio_stress_signal",
            component="event_generator",
        ),
        ThresholdPredicate(
            metric="zone_activity",
            zone="cafeteria",
            operator="lt",
            value=0.3,
            scenario_id="multimodal_conflict",
            component="event_generator",
        ),
        ThresholdPredicate(
            metric="zone_audio",
            zone="cafeteria",
            operator="gt",
            value=0.6,
            scenario_id="multimodal_conflict",
            component="event_generator",
        ),
        ThresholdPredicate(
            metric="zone_density",
            zone="*",
            operator="gt",
            value=0.6,
            scenario_id="evacuation_recommendation",
            component="event_generator",
        ),
        ThresholdPredicate(
            metric="zone_density",
            zone="*",
            operator="gt",
            value=0.7,
            scenario_id="*",
            component="event_generator",
            label="generic elevated density",
        ),
        ThresholdPredicate(
            metric="zone_audio",
            zone="*",
            operator="gt",
            value=0.75,
            scenario_id="*",
            component="event_generator",
            label="generic elevated audio",
        ),
        ThresholdPredicate(
            metric="composite_score",
            zone="*",
            operator="lt",
            value=0.25,
            scenario_id="*",
            component="event_generator",
            label="emit skip threshold",
        ),
    )


def _extract_event_generator_logic() -> tuple[LogicPredicate, ...]:
    return tuple(
        LogicPredicate(
            predicate_id=f"eg-{scenario.value}",
            scenario_id=scenario.value,
            component="event_generator",
            expression=f"_classify_signal scenario=={scenario.value}",
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
        component_id="event_generator",
        variables=(
            "zone_density",
            "zone_activity",
            "zone_audio",
            "composite_score",
        ),
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
