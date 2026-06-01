#!/usr/bin/env python3
"""Basic reproducible simulation example for DUALEXIS.

Run:
    uv run python examples/simulation_basic/run_simulation.py
    uv run python examples/simulation_basic/run_simulation.py --scenario crowd_acceleration --seed 7
    uv run dualexis simulate --scenario exit_blockage --seed 42 --json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dualexis.simulation import run_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a reproducible DUALEXIS simulation scenario")
    parser.add_argument(
        "--scenario",
        default="normal_flow",
        choices=[
            "normal_flow",
            "crowd_acceleration",
            "exit_blockage",
            "audio_stress_signal",
            "multimodal_conflict",
            "evacuation_recommendation",
        ],
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("examples/simulation_basic/output.json"),
        help="Write summary JSON (semantic events only, no raw media)",
    )
    args = parser.parse_args()

    result = run_scenario(args.scenario, seed=args.seed)

    summary = {
        "scenario_id": result.scenario_id.value,
        "seed": result.seed,
        "location_id": result.graph.location_id,
        "zones": [zone.zone_id for zone in result.graph.zones],
        "exits": [exit_node.exit_id for exit_node in result.graph.exits],
        "event_count": len(result.events),
        "ground_truth_primary_label": result.ground_truth.primary_label,
        "recommended_review": result.ground_truth.recommended_review,
        "events": [
            {
                "event_id": str(event.event_id),
                "zone_id": event.zone_id,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "timestamp": event.timestamp.isoformat(),
                "category": event.metadata.get("category"),
                "explanation": event.explanation,
            }
            for event in result.events
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Scenario: {result.scenario_id.value}  seed={result.seed}")
    print(f"Events generated: {len(result.events)}")
    print(f"Ground truth label: {result.ground_truth.primary_label}")
    print(f"Summary written to {args.output}")


if __name__ == "__main__":
    main()
