"""Baseline comparison runner and report generation."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dualexis.evaluation.comparable_baselines import (
    ComparableBaselineId,
    ComparableBaselineResult,
    run_all_comparable_baselines,
)
from dualexis.experiments.multiseed import (
    DescriptiveStats,
    compute_descriptive_stats,
    parse_seed_list,
)

NEUTRALITY_NOTE = "No statistical significance claims or ranking claims are made."

COMPARISON_DISCLAIMER = (
    "Comparable baseline report (synthetic inputs only). "
    "All baselines run on identical scenarios and seeds. "
    f"{NEUTRALITY_NOTE}"
)


class BaselineMetricAggregates(BaseModel):
    """Descriptive aggregates for one baseline across seeds."""

    model_config = ConfigDict(frozen=True)

    baseline_id: str
    end_to_end_latency_ms: DescriptiveStats
    recommendation_count: DescriptiveStats
    privacy_violation_count: DescriptiveStats
    explanation_completeness_score: DescriptiveStats
    human_review_compliance_rate: DescriptiveStats
    modality_drop_tolerance: DescriptiveStats
    reproducibility_score: DescriptiveStats


@dataclass(frozen=True)
class BaselineComparisonReport:
    """Full comparison output for one scenario across seeds and baselines."""

    scenario: str
    seeds: tuple[int, ...]
    generated_at: datetime
    output_dir: str
    disclaimer: str = COMPARISON_DISCLAIMER
    runs: tuple[ComparableBaselineResult, ...] = field(default_factory=tuple)
    aggregates: tuple[BaselineMetricAggregates, ...] = field(default_factory=tuple)


def _aggregate_metric(values: Sequence[float]) -> DescriptiveStats:
    return compute_descriptive_stats(values)


def compute_baseline_aggregates(
    runs: Sequence[ComparableBaselineResult],
) -> tuple[BaselineMetricAggregates, ...]:
    """Compute descriptive aggregates grouped by baseline."""
    grouped: dict[str, list[ComparableBaselineResult]] = {}
    for run in runs:
        grouped.setdefault(run.baseline_id.value, []).append(run)

    aggregates: list[BaselineMetricAggregates] = []
    for baseline_id in sorted(grouped):
        items = grouped[baseline_id]
        aggregates.append(
            BaselineMetricAggregates(
                baseline_id=baseline_id,
                end_to_end_latency_ms=_aggregate_metric(
                    [item.end_to_end_latency_ms for item in items]
                ),
                recommendation_count=_aggregate_metric(
                    [float(item.recommendation_count) for item in items]
                ),
                privacy_violation_count=_aggregate_metric(
                    [float(item.privacy_violation_count) for item in items]
                ),
                explanation_completeness_score=_aggregate_metric(
                    [item.explanation_completeness_score for item in items]
                ),
                human_review_compliance_rate=_aggregate_metric(
                    [item.human_review_compliance_rate for item in items]
                ),
                modality_drop_tolerance=_aggregate_metric(
                    [item.modality_drop_tolerance for item in items]
                ),
                reproducibility_score=_aggregate_metric(
                    [item.reproducibility_score for item in items]
                ),
            )
        )
    return tuple(aggregates)


def run_baseline_comparison(
    scenario: str,
    seeds: Sequence[int],
    *,
    output_dir: str | Path,
) -> BaselineComparisonReport:
    """Run all comparable baselines for each seed and write comparison artifacts."""
    out_root = Path(output_dir).resolve()
    runs_dir = out_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    seed_tuple = tuple(seeds)
    runs: list[ComparableBaselineResult] = []
    for seed in seed_tuple:
        for result in run_all_comparable_baselines(scenario, seed=seed):
            runs.append(result)
            filename = f"{result.baseline_id.value}_{scenario}_seed_{seed}.json"
            path = runs_dir / filename
            path.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")

    aggregates = compute_baseline_aggregates(runs)
    report = BaselineComparisonReport(
        scenario=scenario,
        seeds=seed_tuple,
        generated_at=datetime.now(tz=UTC),
        output_dir=str(out_root),
        runs=tuple(runs),
        aggregates=aggregates,
    )

    serializable_runs = [run.as_dict() for run in runs]
    (out_root / "comparison_summary.json").write_text(
        json.dumps(
            {
                "disclaimer": report.disclaimer,
                "scenario": report.scenario,
                "seeds": list(report.seeds),
                "generated_at": report.generated_at.isoformat(),
                "runs": serializable_runs,
                "aggregates": [item.model_dump(mode="json") for item in aggregates],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    generate_comparison_markdown(report, output_path=out_root / "comparison_report.md")
    generate_comparison_latex_table(report, output_path=out_root / "comparison_results.tex")
    return report


def generate_comparison_markdown(
    report: BaselineComparisonReport,
    *,
    output_path: Path | None = None,
) -> str:
    """Generate a Markdown comparison report."""
    lines = [
        "# DUALEXIS Baseline Comparison Report",
        "",
        f"> {report.disclaimer}",
        "",
        f"Scenario: `{report.scenario}`",
        f"Seeds: {', '.join(str(seed) for seed in report.seeds)}",
        f"Generated at: {report.generated_at.isoformat()}",
        "",
        "## Aggregate metrics (mean ± std)",
        "",
        "| Baseline | E2E latency (ms) | Recommendations | Privacy violations | "
        "Explanation completeness | Review compliance | Drop tolerance | Reproducibility |",
        "| -------- | ---------------- | --------------- | ------------------ | "
        "------------------------ | ----------------- | -------------- | --------------- |",
    ]

    for aggregate in report.aggregates:
        latency = aggregate.end_to_end_latency_ms
        recs = aggregate.recommendation_count
        privacy = aggregate.privacy_violation_count
        explanation = aggregate.explanation_completeness_score
        review = aggregate.human_review_compliance_rate
        drop = aggregate.modality_drop_tolerance
        repro = aggregate.reproducibility_score
        lines.append(
            f"| {aggregate.baseline_id} | "
            f"{latency.mean:.1f} ± {latency.std:.1f} | "
            f"{recs.mean:.2f} ± {recs.std:.2f} | "
            f"{privacy.mean:.2f} | "
            f"{explanation.mean:.3f} ± {explanation.std:.3f} | "
            f"{review.mean:.3f} | "
            f"{drop.mean:.3f} | "
            f"{repro.mean:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- All baselines consume the same synthetic scenario inputs and seeds.",
            f"- {NEUTRALITY_NOTE}",
            "",
        ]
    )

    content = "\n".join(lines)
    if output_path is not None:
        target = output_path.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8")
    return content


def generate_comparison_latex_table(
    report: BaselineComparisonReport,
    *,
    output_path: Path | None = None,
) -> str:
    """Generate a LaTeX comparison table with descriptive aggregates."""
    scenario_label = report.scenario.replace("_", r"\_")
    lines = [
        "% Auto-generated by `dualexis experiment compare`.",
        "% Descriptive comparison only — no significance testing.",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Comparable baseline aggregates on synthetic scenario "
        f"{scenario_label}. "
        "Mean $\\pm$ sample standard deviation; no statistical significance claimed.}",
        "  \\label{tab:baseline-comparison}",
        "  \\small",
        "  \\begin{tabular}{@{}lrrrr@{}}",
        "    \\toprule",
        "    Baseline & $L_{\\mathrm{e2e}}$ (ms) & Recs. & "
        "$N_{\\mathrm{priv}}$ & $S_{\\mathrm{expl}}$ \\\\",
        "    \\midrule",
    ]

    label_map = {
        ComparableBaselineId.SINGLE_MODALITY_ALERT.value: "Single-modality alert",
        ComparableBaselineId.RULE_BASED_FUSION.value: "Rule-based fusion",
        ComparableBaselineId.TEMPORAL_GRAPH.value: "Temporal graph",
        ComparableBaselineId.DUALEXIS_FULL_PIPELINE.value: "DUALEXIS full pipeline",
    }

    for aggregate in report.aggregates:
        label = label_map.get(aggregate.baseline_id, aggregate.baseline_id)
        latency = aggregate.end_to_end_latency_ms
        recs = aggregate.recommendation_count
        privacy = aggregate.privacy_violation_count
        explanation = aggregate.explanation_completeness_score
        lines.append(
            f"    {label} & "
            f"${latency.mean:.1f} \\pm {latency.std:.1f}$ & "
            f"${recs.mean:.1f} \\pm {recs.std:.1f}$ & "
            f"${privacy.mean:.1f}$ & "
            f"${explanation.mean:.2f} \\pm {explanation.std:.2f}$ \\\\"
        )

    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )

    content = "\n".join(lines)
    if output_path is not None:
        target = output_path.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8")
    return content


__all__ = [
    "COMPARISON_DISCLAIMER",
    "NEUTRALITY_NOTE",
    "BaselineComparisonReport",
    "BaselineMetricAggregates",
    "compute_baseline_aggregates",
    "generate_comparison_latex_table",
    "generate_comparison_markdown",
    "parse_seed_list",
    "run_baseline_comparison",
]
