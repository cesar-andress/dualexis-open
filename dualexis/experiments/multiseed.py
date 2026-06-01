"""Multi-seed experimental battery execution and aggregate reporting."""

from __future__ import annotations

import json
import statistics
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from dualexis.experiments.battery import BatteryResult, run_battery
from dualexis.experiments.config import list_experiment_configs, load_experiment_config
from dualexis.experiments.runner import write_battery_json

MULTISEED_DISCLAIMER = (
    "Multi-seed experimental battery (synthetic inputs only). "
    "Aggregates report descriptive statistics (mean, standard deviation, min, max). "
    "No automatic significance testing or empirical conclusions are implied."
)


class DescriptiveStats(BaseModel):
    """Descriptive statistics for a scalar metric across seeds."""

    model_config = ConfigDict(frozen=True)

    mean: float
    std: float
    minimum: float
    maximum: float
    count: int = Field(ge=0)


class ExperimentMetricAggregates(BaseModel):
    """Aggregated metrics for one experiment across multiple seeds."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str = Field(min_length=1, max_length=64)
    scenario: str = Field(min_length=1, max_length=64)
    seeds: tuple[int, ...]
    pipeline_event_count: DescriptiveStats
    end_to_end_latency_ms: DescriptiveStats
    privacy_violation_count: DescriptiveStats
    modality_drop_tolerance: DescriptiveStats


class MultiseedBatteryReport(BaseModel):
    """Full multi-seed battery output bundle."""

    model_config = ConfigDict(frozen=True)

    disclaimer: str = MULTISEED_DISCLAIMER
    generated_at: datetime
    config_dir: str
    output_dir: str
    seeds: tuple[int, ...]
    run_count: int = Field(ge=0)
    runs: tuple[BatteryResult, ...] = Field(default_factory=tuple)
    aggregates: tuple[ExperimentMetricAggregates, ...] = Field(default_factory=tuple)


def parse_seed_list(seeds: str) -> tuple[int, ...]:
    """Parse a comma-separated seed list from CLI input."""
    if not seeds.strip():
        msg = "At least one seed is required"
        raise ValueError(msg)
    parsed = tuple(int(part.strip()) for part in seeds.split(",") if part.strip())
    if not parsed:
        msg = "At least one seed is required"
        raise ValueError(msg)
    return parsed


def compute_descriptive_stats(values: Sequence[float]) -> DescriptiveStats:
    """Compute mean, sample standard deviation, min, and max."""
    count = len(values)
    if count == 0:
        return DescriptiveStats(mean=0.0, std=0.0, minimum=0.0, maximum=0.0, count=0)

    mean = statistics.fmean(values)
    std = 0.0 if count == 1 else statistics.stdev(values)
    return DescriptiveStats(
        mean=mean,
        std=std,
        minimum=min(values),
        maximum=max(values),
        count=count,
    )


def compute_experiment_aggregates(
    experiment_id: str,
    runs: Sequence[BatteryResult],
) -> ExperimentMetricAggregates:
    """Aggregate scalar metrics for one experiment across seed runs."""
    if not runs:
        msg = f"No runs provided for experiment {experiment_id!r}"
        raise ValueError(msg)

    scenario = runs[0].scenario
    seeds = tuple(sorted({run.seed for run in runs}))
    return ExperimentMetricAggregates(
        experiment_id=experiment_id,
        scenario=scenario,
        seeds=seeds,
        pipeline_event_count=compute_descriptive_stats(
            [float(run.pipeline_event_count) for run in runs]
        ),
        end_to_end_latency_ms=compute_descriptive_stats(
            [run.measurement_metrics.end_to_end_latency_ms for run in runs]
        ),
        privacy_violation_count=compute_descriptive_stats(
            [float(run.experiment_metrics.privacy_violation_count) for run in runs]
        ),
        modality_drop_tolerance=compute_descriptive_stats(
            [run.robustness_modality_drop_tolerance for run in runs]
        ),
    )


def compute_multiseed_aggregates(
    runs: Sequence[BatteryResult],
) -> tuple[ExperimentMetricAggregates, ...]:
    """Group runs by experiment and compute descriptive aggregates."""
    grouped: dict[str, list[BatteryResult]] = {}
    for run in runs:
        grouped.setdefault(run.experiment_id, []).append(run)
    return tuple(
        compute_experiment_aggregates(experiment_id, grouped[experiment_id])
        for experiment_id in sorted(grouped)
    )


def generate_multiseed_markdown(
    report: MultiseedBatteryReport,
    *,
    output_path: Path | None = None,
) -> str:
    """Generate a Markdown summary with descriptive aggregates only."""
    lines = [
        "# DUALEXIS Multi-Seed Experimental Battery Report",
        "",
        f"> {report.disclaimer}",
        "",
        f"Generated at: {report.generated_at.isoformat()}",
        f"Config directory: `{report.config_dir}`",
        f"Seeds: {', '.join(str(seed) for seed in report.seeds)}",
        f"Total runs: {report.run_count}",
        "",
        "## Descriptive aggregates (no significance testing)",
        "",
        "| Experiment | Seeds | Events (mean ± std) | E2E ms (mean ± std) | "
        "Privacy violations (mean) | Drop tolerance (mean ± std) |",
        "| ---------- | ----- | ------------------- | ------------------- | "
        "------------------------- | --------------------------- |",
    ]

    for aggregate in report.aggregates:
        events = aggregate.pipeline_event_count
        latency = aggregate.end_to_end_latency_ms
        privacy = aggregate.privacy_violation_count
        tolerance = aggregate.modality_drop_tolerance
        lines.append(
            f"| {aggregate.experiment_id} | {len(aggregate.seeds)} | "
            f"{events.mean:.2f} ± {events.std:.2f} | "
            f"{latency.mean:.2f} ± {latency.std:.2f} | "
            f"{privacy.mean:.2f} | "
            f"{tolerance.mean:.4f} ± {tolerance.std:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Descriptive statistics only; do not infer statistical significance.",
            "- Individual run JSON files are stored under `runs/`.",
            "",
        ]
    )

    content = "\n".join(lines)
    if output_path is not None:
        target = output_path.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8")
    return content


def generate_multiseed_latex_table(
    report: MultiseedBatteryReport,
    *,
    output_path: Path | None = None,
) -> str:
    """Generate a LaTeX table with descriptive multi-seed aggregates."""
    lines = [
        "% Auto-generated by `dualexis experiment run-multiseed`.",
        "% Descriptive aggregates only — no significance testing.",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Multi-seed experimental battery aggregates (synthetic inputs). "
        "Mean $\\pm$ sample standard deviation; min--max ranges are descriptive only. "
        "No statistical significance is claimed.}",
        "  \\label{tab:multiseed-scaffold}",
        "  \\small",
        "  \\begin{tabular}{@{}lrrrr@{}}",
        "    \\toprule",
        "    Experiment & $N$ & Events & $L_{\\mathrm{e2e}}$ (ms) & $T_{\\mathrm{drop}}$ \\\\",
        "    \\midrule",
    ]

    for aggregate in report.aggregates:
        events = aggregate.pipeline_event_count
        latency = aggregate.end_to_end_latency_ms
        tolerance = aggregate.modality_drop_tolerance
        lines.append(
            f"    {aggregate.experiment_id.replace('_', '\\_')} & "
            f"{len(aggregate.seeds)} & "
            f"${events.mean:.1f} \\pm {events.std:.1f}$ "
            f"[{events.minimum:.0f}, {events.maximum:.0f}] & "
            f"${latency.mean:.1f} \\pm {latency.std:.1f}$ & "
            f"${tolerance.mean:.2f} \\pm {tolerance.std:.2f}$ \\\\"
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


def run_multiseed_batteries(
    output_dir: str | Path,
    *,
    config_dir: str | Path,
    seeds: Sequence[int],
) -> MultiseedBatteryReport:
    """Run every config for every seed and write JSON plus aggregate artifacts."""
    config_root = Path(config_dir).resolve()
    out_root = Path(output_dir).resolve()
    runs_dir = out_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    seed_tuple = tuple(seeds)
    runs: list[BatteryResult] = []
    for config_path in list_experiment_configs(config_root):
        config = load_experiment_config(config_path)
        for seed in seed_tuple:
            result = run_battery(config, config_path=str(config_path), seed=seed)
            filename = f"{result.experiment_id}_seed_{seed}.json"
            write_battery_json(result, runs_dir / filename)
            runs.append(result)

    aggregates = compute_multiseed_aggregates(runs)
    report = MultiseedBatteryReport(
        generated_at=datetime.now(tz=UTC),
        config_dir=str(config_root),
        output_dir=str(out_root),
        seeds=seed_tuple,
        run_count=len(runs),
        runs=tuple(runs),
        aggregates=aggregates,
    )

    (out_root / "multiseed_summary.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    (out_root / "aggregates.json").write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in aggregates],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    generate_multiseed_markdown(report, output_path=out_root / "multiseed_report.md")
    generate_multiseed_latex_table(report, output_path=out_root / "multiseed_results.tex")

    return report


__all__ = [
    "MULTISEED_DISCLAIMER",
    "DescriptiveStats",
    "ExperimentMetricAggregates",
    "MultiseedBatteryReport",
    "compute_descriptive_stats",
    "compute_experiment_aggregates",
    "compute_multiseed_aggregates",
    "generate_multiseed_latex_table",
    "generate_multiseed_markdown",
    "parse_seed_list",
    "run_multiseed_batteries",
]
