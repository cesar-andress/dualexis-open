"""E2: independent ground-truth pipeline — authoring, evaluation, and exports."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.evaluation.comparable_baselines import ComparableBaselineId, get_comparable_baseline
from dualexis.experiments.multiseed import DescriptiveStats, compute_descriptive_stats
from dualexis.simulation.ground_truth_loader import (
    dump_scenario_ground_truth_yaml,
    load_scenario_ground_truth,
)
from dualexis.simulation.independent_labeler import build_independent_ground_truth
from dualexis.simulation.scenario import ScenarioId

E2_DISCLAIMER = (
    "E2 synthetic evaluation against independent YAML ground truth authored from "
    "separate rule files. Descriptive multiseed statistics only; no field-effectiveness claim."
)

DEFAULT_SEEDS: tuple[int, ...] = tuple(range(1, 31))

E2_SCENARIOS: tuple[str, ...] = tuple(s.value for s in ScenarioId)

RESULTS_TEX_MARKERS = ("% <e2-auto-tables>", "% </e2-auto-tables>")


@dataclass(frozen=True)
class E2RunRow:
    scenario: str
    seed: int
    gt_label_count: int
    predicted_event_count: int
    event_detection_accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    explanation_completeness_score: float
    privacy_violation_count: int


@dataclass(frozen=True)
class E2AggregateRow:
    scenario: str
    seed_count: int
    detection_accuracy: DescriptiveStats
    false_positive_rate: DescriptiveStats
    false_negative_rate: DescriptiveStats
    explanation_completeness: DescriptiveStats


def regenerate_ground_truth_yaml(
    scenarios: Sequence[str] | None = None,
) -> tuple[Path, ...]:
    """Author ``experiments/ground_truth/*.yaml`` from rules + world dynamics."""
    written: list[Path] = []
    for scenario_id in scenarios or E2_SCENARIOS:
        sid = ScenarioId(scenario_id)
        ground_truth = build_independent_ground_truth(sid, seed=0)
        written.append(
            dump_scenario_ground_truth_yaml(ground_truth, source="e2_rules_pipeline_v1")
        )
    return tuple(written)


def run_e2_evaluation_row(scenario: str, seed: int) -> E2RunRow:
    """Run full DUALEXIS (B5) and score against independent GT YAML."""
    result = get_comparable_baseline(ComparableBaselineId.DUALEXIS_FULL_PIPELINE).run(
        scenario, seed=seed
    )
    ground_truth = load_scenario_ground_truth(ScenarioId(scenario))

    return E2RunRow(
        scenario=scenario,
        seed=seed,
        gt_label_count=len(ground_truth.labels),
        predicted_event_count=0,
        event_detection_accuracy=result.event_detection_accuracy,
        false_positive_rate=result.false_positive_rate,
        false_negative_rate=result.false_negative_rate,
        explanation_completeness_score=result.explanation_completeness_score,
        privacy_violation_count=result.privacy_violation_count,
    )


def run_e2_multiseed(
    scenarios: Sequence[str],
    seeds: Sequence[int],
) -> tuple[E2RunRow, ...]:
    return tuple(run_e2_evaluation_row(scenario, seed) for scenario in scenarios for seed in seeds)


def compute_e2_aggregates(runs: Sequence[E2RunRow]) -> tuple[E2AggregateRow, ...]:
    grouped: dict[str, list[E2RunRow]] = {}
    for run in runs:
        grouped.setdefault(run.scenario, []).append(run)

    rows: list[E2AggregateRow] = []
    for scenario, items in sorted(grouped.items()):
        rows.append(
            E2AggregateRow(
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
            )
        )
    return tuple(rows)


def _write_e2_csv(path: Path, runs: Sequence[E2RunRow]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario",
                "seed",
                "gt_label_count",
                "predicted_event_count",
                "event_detection_accuracy",
                "false_positive_rate",
                "false_negative_rate",
                "explanation_completeness_score",
                "privacy_violation_count",
            ],
        )
        writer.writeheader()
        for row in runs:
            writer.writerow(
                {
                    "scenario": row.scenario,
                    "seed": row.seed,
                    "gt_label_count": row.gt_label_count,
                    "predicted_event_count": row.predicted_event_count,
                    "event_detection_accuracy": round(row.event_detection_accuracy, 4),
                    "false_positive_rate": round(row.false_positive_rate, 4),
                    "false_negative_rate": round(row.false_negative_rate, 4),
                    "explanation_completeness_score": round(
                        row.explanation_completeness_score, 4
                    ),
                    "privacy_violation_count": row.privacy_violation_count,
                }
            )


def generate_e2_latex_table(
    aggregates: Sequence[E2AggregateRow],
    *,
    seed_count: int,
) -> str:
    lines = [
        "% Auto-generated by dualexis experiment e2 (independent ground truth).",
        f"% {E2_DISCLAIMER}",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{E2 evaluation: reference pipeline (B5) vs. independent ground-truth "
        f"YAML labels ($N={seed_count}$ seeds per scenario). Mean detection accuracy and "
        "false-positive rate; synthetic descriptive statistics only.}",
        "  \\label{tab:e2-independent-gt}",
        "  \\small",
        "  \\begin{tabular}{@{}lrrrr@{}}",
        "    \\toprule",
        "    Scenario & Acc. (mean) & FPR (mean) & FNR (mean) & $S_{\\mathrm{expl}}$ (mean) \\\\",
        "    \\midrule",
    ]
    focus = (
        "normal_flow",
        "exit_blockage",
        "multimodal_conflict",
        "evacuation_recommendation",
        "crowd_acceleration",
        "audio_stress_signal",
    )
    by_scenario = {row.scenario: row for row in aggregates}
    for scenario in focus:
        row = by_scenario.get(scenario)
        if row is None:
            continue
        scen_tex = scenario.replace("_", r"\_")
        lines.append(
            f"    {scen_tex} & {row.detection_accuracy.mean:.3f} & "
            f"{row.false_positive_rate.mean:.3f} & "
            f"{row.false_negative_rate.mean:.3f} & "
            f"{row.explanation_completeness.mean:.2f} \\\\"
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


def sync_results_tex(
    results_tex: Path,
    *,
    table_input: str = "tables/e2_independent_gt",
) -> bool:
    """Insert or refresh E2 table ``\\input`` block in ``results_reference/sections/results.tex``."""
    if not results_tex.is_file():
        return False

    block = f"{RESULTS_TEX_MARKERS[0]}\n\\input{{{table_input}}}\n{RESULTS_TEX_MARKERS[1]}"
    text = results_tex.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(RESULTS_TEX_MARKERS[0])
        + r".*?"
        + re.escape(RESULTS_TEX_MARKERS[1]),
        flags=re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(block, text, count=1)
    elif "\\input{tables/e2_independent_gt}" in text:
        updated = text
    else:
        anchor = "\\input{tables/baseline_results}"
        if anchor not in text:
            return False
        updated = text.replace(anchor, f"{block}\n\n{anchor}", 1)

    if updated != text:
        results_tex.write_text(updated, encoding="utf-8")
        return True
    return False


def run_e2_package(
    *,
    output_dir: str | Path = "results/e2_independent_gt",
    paper_tex: str | Path = "results_reference/tables/e2_independent_gt.tex",
    results_tex: str | Path = "results_reference/sections/results.tex",
    scenarios: Sequence[str] | None = None,
    seeds: Sequence[int] | None = None,
    regenerate_yaml: bool = True,
) -> dict[str, object]:
    """Execute E2 pipeline end-to-end."""
    scenario_list = tuple(scenarios or E2_SCENARIOS)
    seed_list = tuple(seeds or DEFAULT_SEEDS)
    out_root = Path(output_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    yaml_paths: tuple[Path, ...] = ()
    if regenerate_yaml:
        yaml_paths = regenerate_ground_truth_yaml(scenario_list)

    runs = run_e2_multiseed(scenario_list, seed_list)
    aggregates = compute_e2_aggregates(runs)

    _write_e2_csv(out_root / "results.csv", runs)
    (out_root / "aggregates.json").write_text(
        json.dumps(
            {
                "disclaimer": E2_DISCLAIMER,
                "seeds": list(seed_list),
                "scenarios": list(scenario_list),
                "aggregates": [
                    {
                        "scenario": row.scenario,
                        "detection_accuracy_mean": row.detection_accuracy.mean,
                        "false_positive_rate_mean": row.false_positive_rate.mean,
                    }
                    for row in aggregates
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    tex_path = Path(paper_tex).resolve()
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text(
        generate_e2_latex_table(aggregates, seed_count=len(seed_list)),
        encoding="utf-8",
    )

    synced = sync_results_tex(Path(results_tex).resolve())

    return {
        "yaml_paths": [str(p) for p in yaml_paths],
        "runs": len(runs),
        "csv": str(out_root / "results.csv"),
        "tex": str(tex_path),
        "results_tex_synced": synced,
    }


__all__ = [
    "DEFAULT_SEEDS",
    "E2_DISCLAIMER",
    "E2_SCENARIOS",
    "regenerate_ground_truth_yaml",
    "run_e2_package",
    "sync_results_tex",
]
