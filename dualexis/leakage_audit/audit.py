"""Run full E2 leakage audit (static overlap + Monte Carlo)."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from dualexis.leakage_audit.dependency_graph import build_dependency_graph_dot
from dualexis.leakage_audit.export import write_leakage_audit_tex, write_leakage_analysis_section
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.leakage_audit.monte_carlo import run_monte_carlo_battery
from dualexis.leakage_audit.overlap import compute_overlap_report
from dualexis.leakage_audit.scoring import (
    BENCHMARK_DISCLOSURE,
    build_independence_estimates,
    compute_leakage_score,
)
from dualexis.leakage_audit.spec_extraction import extract_all_specs
from dualexis.simulation.scenario import ScenarioId

DEFAULT_SCENARIOS: tuple[str, ...] = tuple(s.value for s in ScenarioId)


def run_leakage_audit(
    *,
    output_dir: Path,
    paper_tables: Path | None = None,
    paper_sections: Path | None = None,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    seed: int = 1,
    monte_carlo_iterations: int = 1000,
    fast: bool = False,
) -> LeakageAuditReport:
    """Execute leakage audit and export artefacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    world, events, rules = extract_all_specs()
    overlap = compute_overlap_report(world, events, rules)
    dot = build_dependency_graph_dot(world, events, rules)
    (output_dir / "dependency_graph.dot").write_text(dot, encoding="utf-8")

    specs_payload = {
        "world_dynamics": world.model_dump(),
        "event_generator": events.model_dump(),
        "ground_truth_rules": rules.model_dump(),
    }
    (output_dir / "component_specs.json").write_text(
        json.dumps(specs_payload, indent=2, default=str),
        encoding="utf-8",
    )

    mc_iters = 50 if fast else monte_carlo_iterations
    mc_results = run_monte_carlo_battery(scenarios, seed=seed, iterations=mc_iters)
    gt_stab = sum(r.ground_truth_stability for r in mc_results.values()) / len(mc_results)
    ev_stab = sum(r.event_stability for r in mc_results.values()) / len(mc_results)
    agr_drift = sum(r.agreement_drift for r in mc_results.values()) / len(mc_results)

    independence = build_independence_estimates(
        overlap,
        ground_truth_stability=gt_stab,
        agreement_drift=agr_drift,
    )
    leakage_score = compute_leakage_score(overlap)

    per_scenario = {
        scenario: {
            "ground_truth_stability": round(mc.ground_truth_stability, 4),
            "event_stability": round(mc.event_stability, 4),
            "agreement_drift": round(mc.agreement_drift, 4),
        }
        for scenario, mc in mc_results.items()
    }

    report = LeakageAuditReport(
        leakage_score=leakage_score,
        overlap=overlap,
        independence=independence,
        monte_carlo_iterations=mc_iters,
        ground_truth_stability_mean=round(gt_stab, 4),
        event_stability_mean=round(ev_stab, 4),
        agreement_drift_mean=round(agr_drift, 4),
        benchmark_disclosure=BENCHMARK_DISCLOSURE,
        dependency_graph_dot=dot,
        per_scenario=per_scenario,
    )

    summary = report.model_dump()
    summary["generated_at"] = datetime.now(tz=UTC).isoformat()
    (output_dir / "leakage_audit_report.json").write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    with (output_dir / "monte_carlo_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario",
                "ground_truth_stability",
                "event_stability",
                "agreement_drift",
            ],
        )
        writer.writeheader()
        for scenario, mc in mc_results.items():
            writer.writerow(
                {
                    "scenario": scenario,
                    "ground_truth_stability": mc.ground_truth_stability,
                    "event_stability": mc.event_stability,
                    "agreement_drift": mc.agreement_drift,
                }
            )

    overlap_rows = [
        {
            "metric": "shared_variables_ratio",
            "value": overlap.shared_variables_ratio,
        },
        {
            "metric": "shared_threshold_ratio",
            "value": overlap.shared_threshold_ratio,
        },
        {
            "metric": "shared_logic_ratio",
            "value": overlap.shared_logic_ratio,
        },
        {
            "metric": "leakage_score_LS",
            "value": leakage_score,
        },
        {
            "metric": "procedural_independence",
            "value": independence.procedural_independence,
        },
        {
            "metric": "semantic_independence",
            "value": independence.semantic_independence,
        },
        {
            "metric": "distributional_independence",
            "value": independence.distributional_independence,
        },
    ]
    with (output_dir / "overlap_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(overlap_rows)

    if paper_tables is not None:
        write_leakage_audit_tex(report, mc_results, paper_tables / "leakage_audit.tex")
    if paper_sections is not None:
        write_leakage_analysis_section(report, paper_sections / "leakage_analysis.tex")

    return report


__all__ = ["DEFAULT_SCENARIOS", "run_leakage_audit"]
