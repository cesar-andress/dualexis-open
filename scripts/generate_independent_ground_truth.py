#!/usr/bin/env python3
"""Generate independent ground-truth YAML from E2 rules (no event generator)."""

from __future__ import annotations

from dualexis.simulation.ground_truth_loader import dump_scenario_ground_truth_yaml
from dualexis.simulation.independent_labeler import build_independent_ground_truth
from dualexis.simulation.scenario import ScenarioId


def main() -> None:
    for scenario_id in ScenarioId:
        ground_truth = build_independent_ground_truth(scenario_id, seed=0)
        path = dump_scenario_ground_truth_yaml(
            ground_truth,
            source="e2_rules_pipeline_v1",
        )
        print(f"Wrote {path} ({len(ground_truth.labels)} labels)")


if __name__ == "__main__":
    main()
