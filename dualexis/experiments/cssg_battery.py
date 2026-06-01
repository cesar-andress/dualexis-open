"""Generate CSSG paper artefacts."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.cssg.export import (
    generate_causal_state_graph_pdf,
    pick_example_chain,
    write_causal_chain_figure_tex,
    write_causal_metrics_tex,
    write_causal_reasoning_section,
)
from dualexis.cssg.metrics import (
    CausalGraphMetrics,
    compute_causal_graph_metrics,
    explanation_stability_across_seeds,
    merge_with_stability,
)
from dualexis.cssg.runner import build_cssg_trace_from_scenario
from dualexis.experiments.sssg_battery import PAPER_SCENARIOS
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.scenario import ScenarioId


@dataclass(frozen=True)
class CssgBatteryReport:
    traces_dir: Path
    metrics_csv: Path
    metrics_tex: Path
    section_tex: Path
    figure_pdf: Path
    metrics_by_scenario: dict[str, CausalGraphMetrics]


def run_cssg_battery(
    *,
    output_dir: Path,
    paper_tables: Path,
    paper_figures: Path,
    paper_sections: Path,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> CssgBatteryReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    traces_dir = output_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows: list[dict[str, str | float | int]] = []
    metrics_by_scenario: dict[str, CausalGraphMetrics] = {}
    stability_by_scenario: dict[str, float] = {}
    example_chain = ""

    for scenario in scenarios:
        scenario_traces = []
        scenario_metrics: list[CausalGraphMetrics] = []
        gt = load_scenario_ground_truth(ScenarioId(scenario))

        for seed in seeds:
            trace = build_cssg_trace_from_scenario(scenario, seed=seed)
            scenario_traces.append(trace)
            metrics = compute_causal_graph_metrics(trace, gt)
            scenario_metrics.append(metrics)
            metrics_rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "causal_explanation_depth": metrics.causal_explanation_depth,
                    "root_cause_precision": metrics.root_cause_precision,
                    "causal_path_completeness": metrics.causal_path_completeness,
                    "causal_trace_completeness": metrics.causal_trace_completeness,
                    "explanation_stability": metrics.explanation_stability_across_seeds,
                    "transition_precision": metrics.transition_precision,
                    "transition_recall": metrics.transition_recall,
                }
            )
            trace_path = traces_dir / f"{scenario}_seed{seed}.json"
            trace_path.write_text(trace.model_dump_json(indent=2), encoding="utf-8")

        if scenario_traces:
            stability = explanation_stability_across_seeds(scenario_traces)
            stability_by_scenario[scenario] = stability
            merged = merge_with_stability(scenario_metrics[-1], scenario_traces)
            metrics_by_scenario[scenario] = CausalGraphMetrics(
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
                causal_explanation_depth=sum(
                    m.causal_explanation_depth for m in scenario_metrics
                )
                / len(scenario_metrics),
                root_cause_precision=sum(m.root_cause_precision for m in scenario_metrics)
                / len(scenario_metrics),
                causal_path_completeness=sum(
                    m.causal_path_completeness for m in scenario_metrics
                )
                / len(scenario_metrics),
                explanation_stability_across_seeds=stability,
            )
            if not example_chain:
                example_chain = pick_example_chain(scenario_traces[0])

    metrics_csv = output_dir / "cssg_metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
        if metrics_rows:
            writer = csv.DictWriter(handle, fieldnames=list(metrics_rows[0].keys()))
            writer.writeheader()
            writer.writerows(metrics_rows)

    metrics_tex = paper_tables / "causal_metrics.tex"
    write_causal_metrics_tex(metrics_by_scenario, stability_by_scenario, metrics_tex)

    figure_tex = paper_figures / "causal_state_graph.tex"
    write_causal_chain_figure_tex(figure_tex)
    figure_pdf = paper_figures / "causal_state_graph.pdf"
    generate_causal_state_graph_pdf(figure_pdf)

    section_tex = paper_sections / "causal_reasoning.tex"
    write_causal_reasoning_section(example_chain=example_chain, path=section_tex)

    manifest = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "scenarios": list(scenarios),
        "seeds": list(seeds),
        "metrics_csv": str(metrics_csv),
        "metrics_tex": str(metrics_tex),
        "section_tex": str(section_tex),
        "figure_pdf": str(figure_pdf),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return CssgBatteryReport(
        traces_dir=traces_dir,
        metrics_csv=metrics_csv,
        metrics_tex=metrics_tex,
        section_tex=section_tex,
        figure_pdf=figure_pdf,
        metrics_by_scenario=metrics_by_scenario,
    )


__all__ = ["CssgBatteryReport", "run_cssg_battery"]
