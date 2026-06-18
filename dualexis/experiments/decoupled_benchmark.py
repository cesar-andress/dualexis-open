"""Decoupled procedural agreement benchmark (primary conformance metric)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.evaluation.metrics import events_for_b5_alignment
from dualexis.evaluation.procedural_agreement import (
    BootstrapInterval,
    ProceduralAgreementMetrics,
    aggregate_micro_rates,
    bootstrap_ci,
    procedural_agreement_metrics,
)
from dualexis.evaluation.comparable_baselines import (
    _procedural_ground_truth_for_seed,
)
from dualexis.experiments.empirical_battery import DEFAULT_SEEDS, PAPER_SCENARIOS
from dualexis.leakage_audit.audit import run_leakage_audit
from dualexis.simulation import run_scenario
from dualexis.simulation.emission_mode import EmissionMode

DECOUPLED_DISCLAIMER = (
    "Decoupled procedural agreement benchmark: simulator emission profiles are "
    "independent of frozen ground-truth rule YAML. Metrics describe multiset "
    "agreement on (zone_id, semantic_label) keys, not operational safety or "
    "detector superiority."
)


@dataclass(frozen=True)
class ScenarioAgreementRow:
    scenario: str
    mean_par: float
    par_ci: BootstrapInterval
    mean_fpr: float
    mean_fnr: float
    seed_count: int
    simulator_par: float
    pipeline_par: float


@dataclass(frozen=True)
class DecoupledBenchmarkReport:
    generated_at: datetime
    scenarios: tuple[str, ...]
    seeds: tuple[int, ...]
    leakage_score: float
    distributional_independence: float
    shared_threshold_ratio: float
    aggregate: ProceduralAgreementMetrics
    aggregate_ci: BootstrapInterval
    scenario_rows: tuple[ScenarioAgreementRow, ...]
    disclaimer: str


def _simulator_events(result) -> tuple:
    return tuple(event for event in result.events if event.source.value == "simulator")


def run_decoupled_benchmark(
    *,
    output_dir: Path,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    leakage_fast: bool = True,
) -> DecoupledBenchmarkReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    leakage = run_leakage_audit(
        output_dir=output_dir / "leakage",
        scenarios=scenarios,
        fast=leakage_fast,
    )

    per_run: list[ProceduralAgreementMetrics] = []
    per_run_par_values: list[float] = []
    scenario_metrics: dict[str, list[ProceduralAgreementMetrics]] = {s: [] for s in scenarios}
    scenario_par_values: dict[str, list[float]] = {s: [] for s in scenarios}
    csv_rows: list[dict[str, object]] = []

    for scenario in scenarios:
        for seed in seeds:
            sim = run_scenario(scenario, seed=seed, emission_mode=EmissionMode.DECOUPLED)
            sim_events = _simulator_events(sim)
            sim_metrics = procedural_agreement_metrics(sim_events, sim.ground_truth)

            from dualexis.pipeline import run_pipeline

            pipeline_output = run_pipeline(scenario, seed=seed)
            pipeline_events = events_for_b5_alignment(pipeline_output.normalized_events)
            gt = _procedural_ground_truth_for_seed(scenario, seed)
            pipeline_metrics = procedural_agreement_metrics(pipeline_events, gt)

            per_run.append(sim_metrics)
            per_run_par_values.append(sim_metrics.par)
            scenario_metrics[scenario].append(sim_metrics)
            scenario_par_values[scenario].append(sim_metrics.par)

            csv_rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "par_simulator": sim_metrics.par,
                    "fpr_simulator": sim_metrics.fpr,
                    "fnr_simulator": sim_metrics.fnr,
                    "par_pipeline_b5": pipeline_metrics.par,
                    "fpr_pipeline_b5": pipeline_metrics.fpr,
                    "fnr_pipeline_b5": pipeline_metrics.fnr,
                    "tp": sim_metrics.counts.true_positives,
                    "fp": sim_metrics.counts.false_positives,
                    "fn": sim_metrics.counts.false_negatives,
                }
            )

    aggregate = aggregate_micro_rates(per_run)
    aggregate_ci = bootstrap_ci(per_run_par_values)

    scenario_rows: list[ScenarioAgreementRow] = []
    for scenario in scenarios:
        metrics = scenario_metrics[scenario]
        par_values = scenario_par_values[scenario]
        agg = aggregate_micro_rates(metrics)
        scenario_rows.append(
            ScenarioAgreementRow(
                scenario=scenario,
                mean_par=round(sum(par_values) / len(par_values), 4),
                par_ci=bootstrap_ci(par_values),
                mean_fpr=round(sum(m.fpr for m in metrics) / len(metrics), 4),
                mean_fnr=round(sum(m.fnr for m in metrics) / len(metrics), 4),
                seed_count=len(seeds),
                simulator_par=agg.par,
                pipeline_par=0.0,  # filled below if needed
            )
        )

    report = DecoupledBenchmarkReport(
        generated_at=datetime.now(tz=UTC),
        scenarios=scenarios,
        seeds=seeds,
        leakage_score=leakage.leakage_score,
        distributional_independence=leakage.independence.distributional_independence,
        shared_threshold_ratio=leakage.overlap.shared_threshold_ratio,
        aggregate=aggregate,
        aggregate_ci=aggregate_ci,
        scenario_rows=tuple(scenario_rows),
        disclaimer=DECOUPLED_DISCLAIMER,
    )

    _write_csv(output_dir / "procedural_agreement_results.csv", csv_rows)
    _write_json(output_dir / "procedural_agreement_summary.json", report)
    _write_latex(output_dir / "procedural_agreement.tex", report)
    return report


def run_shared_spec_regression(
    *,
    output_dir: Path,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
) -> dict[str, object]:
    """Shared-spec regression: rule-driven emitter vs procedural GT (expect ~1.0 PAR)."""
    from dualexis.evaluation.harness_b5_alignment import classify_detection_accuracy

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for scenario in scenarios:
        par_values: list[float] = []
        for seed in seeds:
            sim = run_scenario(scenario, seed=seed, emission_mode=EmissionMode.SHARED_SPEC)
            sim_events = _simulator_events(sim)
            metrics = procedural_agreement_metrics(sim_events, sim.ground_truth)
            par_values.append(metrics.par)
            rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "par": metrics.par,
                    "fpr": metrics.fpr,
                    "fnr": metrics.fnr,
                }
            )
        mean_par = sum(par_values) / len(par_values)
        rows.append(
            {
                "scenario": scenario,
                "aggregate": True,
                "mean_par": round(mean_par, 4),
                "label": classify_detection_accuracy(mean_par),
            }
        )

    summary = {
        "mode": "shared_spec_regression",
        "description": "Implementation regression check only; not primary conformance evidence.",
        "rows": rows,
    }
    (output_dir / "shared_spec_regression.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    _write_shared_spec_latex(output_dir / "shared_spec_regression.tex", scenarios, rows)
    return summary


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames = [k for k in rows[0] if k != "aggregate"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(row for row in rows if not row.get("aggregate"))


def _write_json(path: Path, report: DecoupledBenchmarkReport) -> None:
    payload = {
        "generated_at": report.generated_at.isoformat(),
        "scenarios": list(report.scenarios),
        "seeds": list(report.seeds),
        "leakage_score": report.leakage_score,
        "distributional_independence": report.distributional_independence,
        "shared_threshold_ratio": report.shared_threshold_ratio,
        "aggregate_par": report.aggregate.par,
        "aggregate_fpr": report.aggregate.fpr,
        "aggregate_fnr": report.aggregate.fnr,
        "aggregate_par_ci_95": [report.aggregate_ci.lower, report.aggregate_ci.upper],
        "disclaimer": report.disclaimer,
        "scenarios_detail": [
            {
                "scenario": row.scenario,
                "mean_par": row.mean_par,
                "par_ci_95": [row.par_ci.lower, row.par_ci.upper],
                "mean_fpr": row.mean_fpr,
                "mean_fnr": row.mean_fnr,
            }
            for row in report.scenario_rows
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_latex(path: Path, report: DecoupledBenchmarkReport) -> None:
    lines = [
        "% Auto-generated by dualexis decoupled_benchmark.",
        "% Primary conformance benchmark (decoupled emission profiles vs procedural GT).",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Decoupled procedural agreement (PAR) by scenario "
        f"($N={len(report.seeds)}$ seeds). Emission profiles are independent of frozen GT rules. "
        f"Aggregate PAR $={report.aggregate.par:.3f}$ "
        f"$[{report.aggregate_ci.lower:.3f}, {report.aggregate_ci.upper:.3f}]$. "
        f"$L_S={report.leakage_score:.3f}$, "
        f"$\\pi_{{\\mathrm{{dist}}}}={report.distributional_independence:.3f}$. "
        "Not operational safety or detector superiority.}",
        "  \\label{tab:procedural-agreement}",
        "  \\small",
        "  \\begin{tabular}{@{}lrrrr@{}}",
        "    \\toprule",
        "    Scenario & PAR & FPR & FNR & 95\\% CI \\\\",
        "    \\midrule",
    ]
    for row in report.scenario_rows:
        scenario_tex = row.scenario.replace("_", r"\_")
        lines.append(
            f"    {scenario_tex} & {row.mean_par:.3f} & {row.mean_fpr:.3f} & "
            f"{row.mean_fnr:.3f} & [{row.par_ci.lower:.3f}, {row.par_ci.upper:.3f}] \\\\"
        )
    lines.extend(
        [
            "    \\midrule",
            f"    Aggregate & {report.aggregate.par:.3f} & {report.aggregate.fpr:.3f} & "
            f"{report.aggregate.fnr:.3f} & "
            f"[{report.aggregate_ci.lower:.3f}, {report.aggregate_ci.upper:.3f}] \\\\",
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_shared_spec_latex(path: Path, scenarios: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    labels = {
        row["scenario"]: row["label"]
        for row in rows
        if row.get("aggregate") and row.get("scenario") in scenarios
    }
    lines = [
        "% Auto-generated shared-spec regression (NOT primary conformance evidence).",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Shared-spec implementation regression check: rule-driven emitter uses the same "
        "procedural YAML as the GT labeler. For CI/regression only; not independent validation.}",
        "  \\label{tab:shared-spec-regression}",
        "  \\small",
        "  \\begin{tabular}{@{}ll@{}}",
        "    \\toprule",
        "    Scenario & Outcome \\\\",
        "    \\midrule",
    ]
    for scenario in scenarios:
        scenario_tex = scenario.replace("_", r"\_")
        lines.append(f"    {scenario_tex} & {labels.get(scenario, 'N/A')} \\\\")
    lines.extend(["    \\bottomrule", "  \\end{tabular}", "\\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


__all__ = [
    "DECOUPLED_DISCLAIMER",
    "DecoupledBenchmarkReport",
    "ScenarioAgreementRow",
    "run_decoupled_benchmark",
    "run_shared_spec_regression",
]
