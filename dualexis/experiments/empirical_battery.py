"""TSGG validation battery: multiseed diagnostics, ablations, and paper table exports."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.evaluation.comparable_baselines import (
    PAPER_BASELINE_LABELS,
    ComparableBaselineId,
    ComparableBaselineResult,
    get_comparable_baseline,
)
from dualexis.evaluation.privacy_fuzz_battery import (
    PRIVACY_FUZZ_DISCLAIMER,
    export_privacy_fuzz_results,
)
from dualexis.experiments.multiseed import DescriptiveStats, compute_descriptive_stats
from dualexis.experiments.validation_battery import (
    ValidationConditionId,
    run_validation_record,
)

EMPIRICAL_DISCLAIMER = (
    "Synthetic empirical battery with independent ground-truth YAML labels. "
    "Descriptive statistics over matched seeds; no field deployment, legal compliance, "
    "or superiority claims."
)

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
class BaselineAggregateRow:
    """Descriptive stats for one paper baseline and scenario."""

    paper_id: str
    baseline_id: str
    scenario: str
    seed_count: int
    detection_accuracy: DescriptiveStats
    false_positive_rate: DescriptiveStats
    false_negative_rate: DescriptiveStats
    explanation_completeness: DescriptiveStats
    privacy_violations: DescriptiveStats


@dataclass(frozen=True)
class AblationAggregateRow:
    """Layer ablation row (exit_blockage reference scenario)."""

    condition: str
    seed_count: int
    detection_accuracy: DescriptiveStats
    explanation_completeness: DescriptiveStats
    privacy_violations: DescriptiveStats


def run_baseline_multiseed(
    scenarios: Sequence[str],
    seeds: Sequence[int],
) -> tuple[ComparableBaselineResult, ...]:
    """Run B1--B5 (all ComparableBaselineId) for each scenario/seed."""
    runs: list[ComparableBaselineResult] = []
    for scenario in scenarios:
        for seed in seeds:
            for paper_id, baseline_id in PAPER_BASELINE_LABELS.items():
                _ = paper_id
                runs.append(get_comparable_baseline(baseline_id).run(scenario, seed=seed))
    return tuple(runs)


def compute_baseline_aggregates(
    runs: Sequence[ComparableBaselineResult],
) -> tuple[BaselineAggregateRow, ...]:
    """Aggregate by paper baseline label and scenario."""
    paper_by_impl = {v.value: k for k, v in PAPER_BASELINE_LABELS.items()}
    grouped: dict[tuple[str, str], list[ComparableBaselineResult]] = {}
    for run in runs:
        paper_id = paper_by_impl.get(run.baseline_id.value, run.baseline_id.value)
        grouped.setdefault((paper_id, run.scenario), []).append(run)

    rows: list[BaselineAggregateRow] = []
    for (paper_id, scenario), items in sorted(grouped.items()):
        rows.append(
            BaselineAggregateRow(
                paper_id=paper_id,
                baseline_id=items[0].baseline_id.value,
                scenario=scenario,
                seed_count=len(items),
                detection_accuracy=compute_descriptive_stats(
                    [r.event_detection_accuracy for r in items]
                ),
                false_positive_rate=compute_descriptive_stats(
                    [r.false_positive_rate for r in items]
                ),
                false_negative_rate=compute_descriptive_stats(
                    [r.false_negative_rate for r in items]
                ),
                explanation_completeness=compute_descriptive_stats(
                    [r.explanation_completeness_score for r in items]
                ),
                privacy_violations=compute_descriptive_stats(
                    [float(r.privacy_violation_count) for r in items]
                ),
            )
        )
    return tuple(rows)


def run_ablation_multiseed(
    scenario: str,
    seeds: Sequence[int],
) -> tuple:
    """Run full pipeline ablations on one reference scenario."""
    from dualexis.experiments.validation_battery import ValidationRunRecord

    conditions = (
        ValidationConditionId.C4_FULL_PIPELINE,
        ValidationConditionId.ABLATION_NO_L1,
        ValidationConditionId.ABLATION_NO_L4,
        ValidationConditionId.ABLATION_NO_L5,
    )
    runs: list[ValidationRunRecord] = []
    for seed in seeds:
        for condition in conditions:
            runs.append(run_validation_record(condition, scenario, seed=seed))
    return tuple(runs)


def compute_ablation_aggregates(runs) -> tuple[AblationAggregateRow, ...]:
    from dualexis.experiments.validation_battery import ValidationRunRecord

    grouped: dict[str, list[ValidationRunRecord]] = {}
    for run in runs:
        grouped.setdefault(run.condition_id.value, []).append(run)

    labels = {
        ValidationConditionId.C4_FULL_PIPELINE.value: "Full reference pipeline (B5)",
        ValidationConditionId.ABLATION_NO_L1.value: "No L1 privacy runtime",
        ValidationConditionId.ABLATION_NO_L4.value: "No L4 temporal graph",
        ValidationConditionId.ABLATION_NO_L5.value: "No L5 explanation layer",
    }
    rows: list[AblationAggregateRow] = []
    for condition_id, items in sorted(grouped.items()):
        rows.append(
            AblationAggregateRow(
                condition=labels.get(condition_id, condition_id),
                seed_count=len(items),
                detection_accuracy=compute_descriptive_stats(
                    [item.event_detection_accuracy for item in items]
                ),
                explanation_completeness=compute_descriptive_stats(
                    [item.explanation_completeness_score for item in items]
                ),
                privacy_violations=compute_descriptive_stats(
                    [float(item.privacy_violation_count) for item in items]
                ),
            )
        )
    return tuple(rows)


def _write_baseline_csv(path: Path, runs: Sequence[ComparableBaselineResult]) -> None:
    paper_by_impl = {v.value: k for k, v in PAPER_BASELINE_LABELS.items()}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_baseline",
                "baseline_id",
                "scenario",
                "seed",
                "event_detection_accuracy",
                "false_positive_rate",
                "false_negative_rate",
                "explanation_completeness_score",
                "privacy_violation_count",
                "end_to_end_latency_ms",
            ],
        )
        writer.writeheader()
        for run in runs:
            writer.writerow(
                {
                    "paper_baseline": paper_by_impl.get(
                        run.baseline_id.value, run.baseline_id.value
                    ),
                    "baseline_id": run.baseline_id.value,
                    "scenario": run.scenario,
                    "seed": run.seed,
                    "event_detection_accuracy": round(run.event_detection_accuracy, 4),
                    "false_positive_rate": round(run.false_positive_rate, 4),
                    "false_negative_rate": round(run.false_negative_rate, 4),
                    "explanation_completeness_score": round(
                        run.explanation_completeness_score, 4
                    ),
                    "privacy_violation_count": run.privacy_violation_count,
                    "end_to_end_latency_ms": round(run.end_to_end_latency_ms, 2),
                }
            )


def _write_summary_md(
    path: Path,
    *,
    baseline_aggs: Sequence[BaselineAggregateRow],
    ablation_aggs: Sequence[AblationAggregateRow],
    seeds: Sequence[int],
) -> None:
    lines = [
        "# DUALEXIS baseline comparison (synthetic, independent GT)",
        "",
        f"> {EMPIRICAL_DISCLAIMER}",
        "",
        f"Generated: {datetime.now(tz=UTC).isoformat()}",
        f"Seeds: {len(seeds)} ({seeds[0]}--{seeds[-1]})",
        "",
        "## B1--B5 aggregates (mean detection accuracy)",
        "",
        "| Baseline | Scenario | Acc. mean | FPR mean | FNR mean | Expl. mean |",
        "| -------- | -------- | --------- | -------- | -------- | ---------- |",
    ]
    for row in baseline_aggs:
        lines.append(
            f"| {row.paper_id} | {row.scenario} | "
            f"{row.detection_accuracy.mean:.3f} | "
            f"{row.false_positive_rate.mean:.3f} | "
            f"{row.false_negative_rate.mean:.3f} | "
            f"{row.explanation_completeness.mean:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Layer ablations (exit_blockage)",
            "",
            "| Condition | Acc. mean | Expl. mean | Privacy viol. mean |",
            "| --------- | --------- | ---------- | ------------------ |",
        ]
    )
    for row in ablation_aggs:
        lines.append(
            f"| {row.condition} | {row.detection_accuracy.mean:.3f} | "
            f"{row.explanation_completeness.mean:.3f} | {row.privacy_violations.mean:.1f} |"
        )
    lines.extend(["", f"> {PRIVACY_FUZZ_DISCLAIMER}", ""])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_baseline_results_latex(
    baseline_aggs: Sequence[BaselineAggregateRow],
    ablation_aggs: Sequence[AblationAggregateRow],
    *,
    seed_count: int,
) -> str:
    """LaTeX tables for baseline_results.tex."""
    lines = [
        "% Auto-generated by dualexis experiment validate-tsgg.",
        "% Independent ground truth; descriptive multiseed aggregates only.",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Multiseed baseline comparison (B1--B5) on synthetic scenarios with "
        f"independent ground-truth labels ($N={seed_count}$ seeds per cell). "
        "Mean detection accuracy and false-positive rate; no inferential superiority claimed.}",
        "  \\label{tab:baseline-multiseed}",
        "  \\label{tab:experimental-battery-scaffold}",
        "  \\small",
        "  \\begin{tabular}{@{}llrrr@{}}",
        "    \\toprule",
        "    Scenario & Baseline & Acc. (mean) & FPR (mean) & $S_{\\mathrm{expl}}$ (mean) \\\\",
        "    \\midrule",
    ]

    focus = ("normal_flow", "exit_blockage", "multimodal_conflict", "evacuation_recommendation")
    for scenario in focus:
        scenario_rows = [r for r in baseline_aggs if r.scenario == scenario]
        for row in sorted(scenario_rows, key=lambda r: r.paper_id):
            scen_tex = row.scenario.replace("_", r"\_")
            lines.append(
                f"    {scen_tex} & {row.paper_id} & "
                f"{row.detection_accuracy.mean:.3f} & "
                f"{row.false_positive_rate.mean:.3f} & "
                f"{row.explanation_completeness.mean:.2f} \\\\"
            )

    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
            "\\begin{table}[htbp]",
            "  \\centering",
            "  \\caption{Layer ablations on \\texttt{exit\\_blockage} "
            f"($N={seed_count}$ seeds). Full reference pipeline (B5) vs. disabled L1, L4, and L5."
            "}",
            "  \\label{tab:baseline-ablations}",
            "  \\small",
            "  \\begin{tabular}{@{}lrrr@{}}",
            "    \\toprule",
            "    Condition & Acc. (mean) & $S_{\\mathrm{expl}}$ (mean) & $N_{\\mathrm{priv}}$ (mean) \\\\",
            "    \\midrule",
        ]
    )
    for row in ablation_aggs:
        lines.append(
            f"    {row.condition} & {row.detection_accuracy.mean:.3f} & "
            f"{row.explanation_completeness.mean:.2f} & {row.privacy_violations.mean:.1f} \\\\"
        )
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def run_empirical_eswa_package(
    *,
    baseline_output: str | Path = "results/baseline_comparison",
    privacy_output: str | Path = "results/privacy_fuzz",
    paper_baseline_tex: str | Path = "results_reference/tables/baseline_results.tex",
    paper_privacy_tex: str | Path = "results_reference/tables/privacy_fuzz_results.tex",
    scenarios: Sequence[str] | None = None,
    seeds: Sequence[int] | None = None,
) -> dict[str, object]:
    """Execute full empirical package and write all exports."""
    scenario_list = tuple(scenarios or PAPER_SCENARIOS)
    seed_list = tuple(seeds or DEFAULT_SEEDS)

    baseline_dir = Path(baseline_output).resolve()
    baseline_dir.mkdir(parents=True, exist_ok=True)

    runs = run_baseline_multiseed(scenario_list, seed_list)
    baseline_aggs = compute_baseline_aggregates(runs)
    ablation_runs = run_ablation_multiseed("exit_blockage", seed_list)
    ablation_aggs = compute_ablation_aggregates(ablation_runs)

    _write_baseline_csv(baseline_dir / "results.csv", runs)
    _write_summary_md(
        baseline_dir / "summary.md",
        baseline_aggs=baseline_aggs,
        ablation_aggs=ablation_aggs,
        seeds=seed_list,
    )
    (baseline_dir / "aggregates.json").write_text(
        json.dumps(
            {
                "disclaimer": EMPIRICAL_DISCLAIMER,
                "seeds": list(seed_list),
                "scenarios": list(scenario_list),
                "baseline_aggregates": [
                    {
                        "paper_id": r.paper_id,
                        "scenario": r.scenario,
                        "detection_accuracy_mean": r.detection_accuracy.mean,
                        "false_positive_rate_mean": r.false_positive_rate.mean,
                    }
                    for r in baseline_aggs
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    tex_path = Path(paper_baseline_tex).resolve()
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text(
        generate_baseline_results_latex(baseline_aggs, ablation_aggs, seed_count=len(seed_list)),
        encoding="utf-8",
    )

    fuzz_csv = export_privacy_fuzz_results(
        privacy_output,
        latex_path=paper_privacy_tex,
    )

    return {
        "baseline_runs": len(runs),
        "baseline_csv": str(baseline_dir / "results.csv"),
        "baseline_tex": str(tex_path),
        "privacy_csv": str(fuzz_csv),
        "privacy_tex": str(Path(paper_privacy_tex).resolve()),
    }


__all__ = [
    "DEFAULT_SEEDS",
    "EMPIRICAL_DISCLAIMER",
    "PAPER_SCENARIOS",
    "run_empirical_eswa_package",
]
