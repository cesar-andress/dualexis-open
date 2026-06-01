"""Generate SSSG paper artefacts and export state-transition traces."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.sssg.export import (
    export_trace_json,
    generate_semantic_state_graph_pdf,
    write_state_transition_examples_tex,
)
from dualexis.sssg.metrics import StateGraphMetrics
from dualexis.sssg.runner import evaluate_sssg_trace

DEFAULT_SEEDS: tuple[int, ...] = tuple(range(1, 31))
PAPER_SCENARIOS: tuple[str, ...] = (
    "normal_flow",
    "exit_blockage",
    "multimodal_conflict",
    "evacuation_recommendation",
    "crowd_acceleration",
    "audio_stress_signal",
)


@dataclass(frozen=True)
class SssgBatteryReport:
    """Paths and aggregate metrics from an SSSG export run."""

    traces_dir: Path
    metrics_csv: Path
    examples_tex: Path
    figure_pdf: Path
    metrics_by_scenario: dict[str, StateGraphMetrics]


def run_sssg_battery(
    *,
    output_dir: Path,
    paper_tables: Path,
    paper_figures: Path,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3),
) -> SssgBatteryReport:
    """Run SSSG on selected scenarios/seeds and write paper artefacts."""
    traces_dir = output_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    metrics_rows: list[dict[str, str | float | int]] = []
    example_traces = []
    metrics_by_scenario: dict[str, StateGraphMetrics] = {}

    for scenario in scenarios:
        scenario_metrics: list[StateGraphMetrics] = []
        for seed in seeds:
            trace, metrics = evaluate_sssg_trace(scenario, seed=seed)
            export_trace_json(trace, traces_dir / f"{scenario}_seed{seed}.json")
            scenario_metrics.append(metrics)
            metrics_rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "transition_precision": round(metrics.transition_precision, 4),
                    "transition_recall": round(metrics.transition_recall, 4),
                    "state_consistency": round(metrics.state_consistency, 4),
                    "causal_trace_completeness": round(metrics.causal_trace_completeness, 4),
                    "predicted_transitions": metrics.predicted_transitions,
                    "expected_transitions": metrics.expected_transitions,
                    "matched_transitions": metrics.matched_transitions,
                    "transition_count": len(trace.transitions),
                }
            )
            if seed == seeds[0]:
                example_traces.append(trace)

        if scenario_metrics:
            metrics_by_scenario[scenario] = StateGraphMetrics(
                transition_precision=sum(m.transition_precision for m in scenario_metrics)
                / len(scenario_metrics),
                transition_recall=sum(m.transition_recall for m in scenario_metrics)
                / len(scenario_metrics),
                state_consistency=sum(m.state_consistency for m in scenario_metrics)
                / len(scenario_metrics),
                causal_trace_completeness=sum(
                    m.causal_trace_completeness for m in scenario_metrics
                )
                / len(scenario_metrics),
                predicted_transitions=scenario_metrics[0].predicted_transitions,
                expected_transitions=scenario_metrics[0].expected_transitions,
                matched_transitions=scenario_metrics[0].matched_transitions,
            )

    metrics_csv = output_dir / "sssg_metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
        if metrics_rows:
            writer = csv.DictWriter(handle, fieldnames=list(metrics_rows[0]))
            writer.writeheader()
            writer.writerows(metrics_rows)

    examples_tex = paper_tables / "state_transition_examples.tex"
    write_state_transition_examples_tex(example_traces, metrics_by_scenario, examples_tex)

    figure_pdf = paper_figures / "semantic_state_graph.pdf"
    generate_semantic_state_graph_pdf(figure_pdf)

    manifest = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "scenarios": list(scenarios),
        "seeds": list(seeds),
        "metrics_csv": str(metrics_csv),
        "examples_tex": str(examples_tex),
        "figure_pdf": str(figure_pdf),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return SssgBatteryReport(
        traces_dir=traces_dir,
        metrics_csv=metrics_csv,
        examples_tex=examples_tex,
        figure_pdf=figure_pdf,
        metrics_by_scenario=metrics_by_scenario,
    )


__all__ = [
    "DEFAULT_SEEDS",
    "PAPER_SCENARIOS",
    "SssgBatteryReport",
    "run_sssg_battery",
]
