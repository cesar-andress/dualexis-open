"""Dependency graph for E2 leakage audit."""

from __future__ import annotations

from dualexis.leakage_audit.models import ComponentSpec
from dualexis.leakage_audit.overlap import pairwise_threshold_alignment


def build_dependency_graph_dot(
    world: ComponentSpec,
    events: ComponentSpec,
    rules: ComponentSpec,
) -> str:
    """Emit Graphviz DOT with shared-metric edges."""
    edges: list[str] = []
    pairs = (
        (world, events, "shared_world_variables"),
        (world, rules, "shared_world_metrics"),
        (events, rules, "shared_thresholds"),
    )
    for left, right, label in pairs:
        var_overlap = set(left.variables) & set(right.variables)
        if var_overlap:
            edges.append(
                f'  {left.component_id} -> {right.component_id} '
                f'[label="{label}: {", ".join(sorted(var_overlap)[:3])}"]; '
                f'weight={len(var_overlap)}];'
            )
        align = pairwise_threshold_alignment(left, right)
        if align > 0.05:
            edges.append(
                f'  {left.component_id} -> {right.component_id} '
                f'[label="threshold_align={align:.2f}", style=dashed];'
            )

    lines = [
        "digraph E2Leakage {",
        '  rankdir=LR;',
        '  node [shape=box, style=rounded];',
        f'  {world.component_id} [label="world_dynamics\\n(shared dynamics)"];',
        f'  {events.component_id} [label="event_generator\\n(emission)"];',
        f'  {rules.component_id} [label="ground_truth_rules\\n(labeling)"];',
        '  independent_labeler [label="independent_labeler", style=dashed];',
        f'  {rules.component_id} -> independent_labeler [label="authoring", style=dotted];',
        f'  {world.component_id} -> {events.component_id} [label="feeds WorldState"];',
        f'  {world.component_id} -> {rules.component_id} [label="feeds metrics"];',
    ]
    lines.extend(edges)
    lines.append("}")
    return "\n".join(lines)


__all__ = ["build_dependency_graph_dot"]
