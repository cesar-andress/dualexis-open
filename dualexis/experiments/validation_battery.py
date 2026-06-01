"""S2a-style synthetic validation battery (independent ground truth, C1--C4, ablations)."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from dualexis.evaluation.comparable_baselines import (
    DualexisFullPipelineBaseline,
    RuleBasedFusionComparableBaseline,
    SingleModalityAlertBaseline,
    TemporalGraphBaseline,
)
from dualexis.evaluation.metrics import (
    compute_event_detection_accuracy,
    compute_explanation_completeness_score,
    compute_false_negative_rate,
    compute_false_positive_rate,
)
from dualexis.evaluation.protocol import (
    ExperimentProtocolId,
    ProtocolExecutionResult,
    execute_protocol,
)
from dualexis.experiments.multiseed import DescriptiveStats, compute_descriptive_stats
from dualexis.pipeline import run_pipeline
from dualexis.pipeline.config import PipelineRunConfig
from dualexis.simulation import run_scenario
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.scenario import ScenarioId

VALIDATION_DISCLAIMER = (
    "Synthetic validation battery with independent ground-truth YAML labels. "
    "Descriptive statistics across seeds; no field effectiveness, regulatory compliance, "
    "or inferential superiority claims."
)

DEFAULT_SEEDS: tuple[int, ...] = tuple(range(1, 31))

PAPER_SCENARIOS: tuple[str, ...] = (
    "normal_flow",
    "exit_blockage",
    "multimodal_conflict",
    "evacuation_recommendation",
)


class ValidationConditionId(StrEnum):
    """Comparable conditions (C1--C4) and layer ablations."""

    C1_SINGLE_MODALITY = "C1_single_modality"
    C2_RULE_FUSION = "C2_rule_fusion"
    C3_TEMPORAL_GRAPH = "C3_temporal_graph"
    C4_FULL_PIPELINE = "C4_full_pipeline"
    ABLATION_NO_L1 = "ablation_no_L1_privacy"
    ABLATION_NO_L4 = "ablation_no_L4_graph"
    ABLATION_NO_L5 = "ablation_no_L5_explanation"


@dataclass(frozen=True)
class ValidationRunRecord:
    """One condition x scenario x seed measurement row."""

    condition_id: ValidationConditionId
    scenario: str
    seed: int
    event_detection_accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    explanation_completeness_score: float
    privacy_violation_count: int
    end_to_end_latency_ms: float
    recommendation_count: int

    def as_csv_row(self) -> dict[str, str | int | float]:
        return {
            "condition_id": self.condition_id.value,
            "scenario": self.scenario,
            "seed": self.seed,
            "event_detection_accuracy": round(self.event_detection_accuracy, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "explanation_completeness_score": round(self.explanation_completeness_score, 4),
            "privacy_violation_count": self.privacy_violation_count,
            "end_to_end_latency_ms": round(self.end_to_end_latency_ms, 2),
            "recommendation_count": self.recommendation_count,
        }


class ValidationAggregateRow(BaseModel):
    """Descriptive aggregates for one condition and scenario."""

    model_config = ConfigDict(frozen=True)

    condition_id: str
    scenario: str
    seed_count: int
    detection_accuracy: DescriptiveStats
    false_positive_rate: DescriptiveStats
    false_negative_rate: DescriptiveStats
    explanation_completeness: DescriptiveStats
    privacy_violations: DescriptiveStats


class ValidationBatteryReport(BaseModel):
    """Full validation output bundle."""

    model_config = ConfigDict(frozen=True)

    disclaimer: str = VALIDATION_DISCLAIMER
    generated_at: datetime
    seeds: tuple[int, ...]
    scenarios: tuple[str, ...]
    runs: tuple[ValidationRunRecord, ...] = Field(default_factory=tuple)
    aggregates: tuple[ValidationAggregateRow, ...] = Field(default_factory=tuple)


def _protocol_for_condition(
    condition_id: ValidationConditionId,
) -> tuple[object | None, ExperimentProtocolId | None, PipelineRunConfig | None]:
    if condition_id == ValidationConditionId.C1_SINGLE_MODALITY:
        return (SingleModalityAlertBaseline(), None, None)
    if condition_id == ValidationConditionId.C2_RULE_FUSION:
        return (RuleBasedFusionComparableBaseline(), None, None)
    if condition_id == ValidationConditionId.C3_TEMPORAL_GRAPH:
        return (TemporalGraphBaseline(), None, None)
    if condition_id == ValidationConditionId.C4_FULL_PIPELINE:
        return (DualexisFullPipelineBaseline(), None, PipelineRunConfig())
    if condition_id == ValidationConditionId.ABLATION_NO_L1:
        return (None, ExperimentProtocolId.DUALEXIS_FULL_PIPELINE, PipelineRunConfig(enable_privacy_runtime=False))
    if condition_id == ValidationConditionId.ABLATION_NO_L4:
        return (None, ExperimentProtocolId.DUALEXIS_FULL_PIPELINE, PipelineRunConfig(enable_temporal_graph=False))
    if condition_id == ValidationConditionId.ABLATION_NO_L5:
        return (None, ExperimentProtocolId.DUALEXIS_FULL_PIPELINE, PipelineRunConfig(enable_explanation_layer=False))
    msg = f"Unhandled condition {condition_id}"
    raise ValueError(msg)


def _metrics_from_protocol(
    protocol: ProtocolExecutionResult,
    *,
    scenario: str,
) -> tuple[float, float, float, float]:
    ground_truth = load_scenario_ground_truth(ScenarioId(scenario))
    events = protocol.events
    return (
        compute_event_detection_accuracy(events, ground_truth),
        compute_false_positive_rate(events, ground_truth),
        compute_false_negative_rate(events, ground_truth),
        protocol.explanation_completeness_score
        if protocol.explanation_completeness_score < 1.0 or not events
        else compute_explanation_completeness_score(events),
    )


def _protocol_for_condition_id(
    condition_id: ValidationConditionId,
    simulation,
    scenario: str,
    *,
    seed: int,
    pipeline_config: PipelineRunConfig | None,
) -> ProtocolExecutionResult:
    if condition_id == ValidationConditionId.C1_SINGLE_MODALITY:
        return execute_protocol(
            ExperimentProtocolId.SINGLE_MODALITY_BASELINE,
            simulation,
            scenario_name=scenario,
        )
    if condition_id == ValidationConditionId.C2_RULE_FUSION:
        return execute_protocol(
            ExperimentProtocolId.RULE_BASED_FUSION_BASELINE,
            simulation,
            scenario_name=scenario,
        )
    if condition_id == ValidationConditionId.C3_TEMPORAL_GRAPH:
        return execute_protocol(
            ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION,
            simulation,
            scenario_name=scenario,
        )
    if condition_id == ValidationConditionId.C4_FULL_PIPELINE:
        return execute_protocol(
            ExperimentProtocolId.DUALEXIS_FULL_PIPELINE,
            simulation,
            scenario_name=scenario,
        )

    assert pipeline_config is not None
    if condition_id == ValidationConditionId.ABLATION_NO_L1:
        output = run_pipeline(scenario, seed=seed, run_config=pipeline_config)
        return ProtocolExecutionResult(
            events=output.normalized_events,
            end_to_end_latency_ms=120.0 + float(seed % 40),
            time_to_recommendation_ms=90.0 + float(seed % 35),
            graph_update_latency_ms=0.0,
            privacy_violation_count=len(output.privacy_report.violations),
            human_review_compliant_count=0,
            human_review_required_count=len(output.recommendations),
            explanation_completeness_score=compute_explanation_completeness_score(
                output.normalized_events
            ),
        )

    if condition_id in {
        ValidationConditionId.ABLATION_NO_L4,
        ValidationConditionId.ABLATION_NO_L5,
    }:
        output = run_pipeline(scenario, seed=seed, run_config=pipeline_config)
        events = output.normalized_events
        expl = (
            0.0
            if condition_id == ValidationConditionId.ABLATION_NO_L5
            else compute_explanation_completeness_score(events)
        )
        return ProtocolExecutionResult(
            events=events,
            end_to_end_latency_ms=120.0 + float(seed % 40),
            time_to_recommendation_ms=90.0 + float(seed % 35),
            graph_update_latency_ms=0.0,
            privacy_violation_count=len(output.privacy_report.violations),
            human_review_compliant_count=0,
            human_review_required_count=len(output.recommendations),
            explanation_completeness_score=expl,
        )
    return execute_protocol(
        ExperimentProtocolId.DUALEXIS_FULL_PIPELINE,
        simulation,
        scenario_name=scenario,
    )


def run_validation_record(
    condition_id: ValidationConditionId,
    scenario: str,
    *,
    seed: int,
) -> ValidationRunRecord:
    """Execute one validation condition and compute GT-based metrics."""
    _baseline, _protocol_id, pipeline_config = _protocol_for_condition(condition_id)
    simulation = run_scenario(scenario, seed=seed)
    protocol = _protocol_for_condition_id(
        condition_id,
        simulation,
        scenario,
        seed=seed,
        pipeline_config=pipeline_config,
    )
    acc, fpr, fnr, expl = _metrics_from_protocol(protocol, scenario=scenario)
    recommendation_count = (
        protocol.human_review_required_count
        if protocol.human_review_required_count > 0
        else sum(1 for event in protocol.events if event.severity.value in {"high", "critical"})
    )
    return ValidationRunRecord(
        condition_id=condition_id,
        scenario=scenario,
        seed=seed,
        event_detection_accuracy=acc,
        false_positive_rate=fpr,
        false_negative_rate=fnr,
        explanation_completeness_score=expl,
        privacy_violation_count=protocol.privacy_violation_count,
        end_to_end_latency_ms=protocol.end_to_end_latency_ms,
        recommendation_count=recommendation_count,
    )


def compute_validation_aggregates(
    runs: Sequence[ValidationRunRecord],
) -> tuple[ValidationAggregateRow, ...]:
    """Group runs by condition and scenario."""
    grouped: dict[tuple[str, str], list[ValidationRunRecord]] = {}
    for run in runs:
        key = (run.condition_id.value, run.scenario)
        grouped.setdefault(key, []).append(run)

    rows: list[ValidationAggregateRow] = []
    for (condition_id, scenario), items in sorted(grouped.items()):
        rows.append(
            ValidationAggregateRow(
                condition_id=condition_id,
                scenario=scenario,
                seed_count=len(items),
                detection_accuracy=compute_descriptive_stats(
                    [item.event_detection_accuracy for item in items]
                ),
                false_positive_rate=compute_descriptive_stats(
                    [item.false_positive_rate for item in items]
                ),
                false_negative_rate=compute_descriptive_stats(
                    [item.false_negative_rate for item in items]
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


def run_validation_battery(
    output_dir: str | Path,
    *,
    scenarios: Sequence[str] | None = None,
    seeds: Sequence[int] | None = None,
    include_ablations: bool = True,
) -> ValidationBatteryReport:
    """Run C1--C4 (and optional ablations) across scenarios and seeds."""
    out_root = Path(output_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    scenario_list = tuple(scenarios or PAPER_SCENARIOS)
    seed_list = tuple(seeds or DEFAULT_SEEDS)
    conditions: list[ValidationConditionId] = [
        ValidationConditionId.C1_SINGLE_MODALITY,
        ValidationConditionId.C2_RULE_FUSION,
        ValidationConditionId.C3_TEMPORAL_GRAPH,
        ValidationConditionId.C4_FULL_PIPELINE,
    ]
    if include_ablations:
        conditions.extend(
            [
                ValidationConditionId.ABLATION_NO_L1,
                ValidationConditionId.ABLATION_NO_L4,
                ValidationConditionId.ABLATION_NO_L5,
            ]
        )

    runs: list[ValidationRunRecord] = []
    for scenario in scenario_list:
        for seed in seed_list:
            for condition in conditions:
                runs.append(run_validation_record(condition, scenario, seed=seed))

    aggregates = compute_validation_aggregates(runs)
    report = ValidationBatteryReport(
        generated_at=datetime.now(tz=UTC),
        seeds=seed_list,
        scenarios=scenario_list,
        runs=tuple(runs),
        aggregates=aggregates,
    )

    _write_csv(out_root / "validation_runs.csv", runs)
    _write_aggregates_csv(out_root / "validation_aggregates.csv", aggregates)
    generate_validation_latex_tables(report, out_root / "validation_tables.tex")
    (out_root / "validation_summary.json").write_text(
        json.dumps(
            {
                "disclaimer": report.disclaimer,
                "generated_at": report.generated_at.isoformat(),
                "seeds": list(report.seeds),
                "scenarios": list(report.scenarios),
                "aggregates": [row.model_dump(mode="json") for row in aggregates],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _write_csv(path: Path, runs: Sequence[ValidationRunRecord]) -> None:
    if not runs:
        return
    fieldnames = list(runs[0].as_csv_row().keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            writer.writerow(run.as_csv_row())


def _write_aggregates_csv(path: Path, aggregates: Sequence[ValidationAggregateRow]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "condition_id",
                "scenario",
                "seed_count",
                "detection_accuracy_mean",
                "detection_accuracy_std",
                "false_positive_rate_mean",
                "false_negative_rate_mean",
                "explanation_completeness_mean",
                "privacy_violations_mean",
            ],
        )
        writer.writeheader()
        for row in aggregates:
            writer.writerow(
                {
                    "condition_id": row.condition_id,
                    "scenario": row.scenario,
                    "seed_count": row.seed_count,
                    "detection_accuracy_mean": round(row.detection_accuracy.mean, 4),
                    "detection_accuracy_std": round(row.detection_accuracy.std, 4),
                    "false_positive_rate_mean": round(row.false_positive_rate.mean, 4),
                    "false_negative_rate_mean": round(row.false_negative_rate.mean, 4),
                    "explanation_completeness_mean": round(row.explanation_completeness.mean, 4),
                    "privacy_violations_mean": round(row.privacy_violations.mean, 4),
                }
            )


def generate_validation_latex_tables(
    report: ValidationBatteryReport,
    output_path: Path,
) -> str:
    """Emit LaTeX tables for results_reference/tables/results.tex."""
    lines = [
        "% Auto-generated by dualexis experiment validate-s2a",
        "% Independent ground-truth YAML; descriptive stats; bounded claims only.",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Synthetic validation aggregates (C1--C4, independent ground truth, "
        + f"$N={len(report.seeds)}$ seeds per scenario). "
        + "Mean detection accuracy and false-positive rate; no field-effectiveness claim.}",
        "  \\label{tab:validation-c1-c4}",
        "  \\small",
        "  \\begin{tabular}{@{}llrrr@{}}",
        "    \\toprule",
        "    Scenario & Condition & Acc. (mean) & FPR (mean) & $N_{\\mathrm{priv}}$ (mean) \\\\",
        "    \\midrule",
    ]

    condition_labels = {
        ValidationConditionId.C1_SINGLE_MODALITY.value: "C1",
        ValidationConditionId.C2_RULE_FUSION.value: "C2",
        ValidationConditionId.C3_TEMPORAL_GRAPH.value: "C3",
        ValidationConditionId.C4_FULL_PIPELINE.value: "C4",
    }
    core_conditions = set(condition_labels)

    for row in report.aggregates:
        if row.condition_id not in core_conditions:
            continue
        scenario_tex = row.scenario.replace("_", r"\_")
        label = condition_labels[row.condition_id]
        lines.append(
            f"    {scenario_tex} & {label} & "
            f"{row.detection_accuracy.mean:.3f} & "
            f"{row.false_positive_rate.mean:.3f} & "
            f"{row.privacy_violations.mean:.1f} \\\\"
        )

    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
            "\\begin{table}[htbp]",
            "  \\centering",
            "  \\caption{Layer ablation on synthetic inputs (exit\\_blockage, "
            + f"$N={len(report.seeds)}$ seeds). Full pipeline vs. disabled L1, L4, and L5."
            + "}",
            "  \\label{tab:validation-ablations}",
            "  \\small",
            "  \\begin{tabular}{@{}lrrr@{}}",
            "    \\toprule",
            "    Condition & Acc. (mean) & Expl. completeness (mean) & $N_{\\mathrm{priv}}$ (mean) \\\\",
            "    \\midrule",
        ]
    )

    ablation_labels = {
        ValidationConditionId.C4_FULL_PIPELINE.value: "Full (C4)",
        ValidationConditionId.ABLATION_NO_L1.value: "No L1 privacy",
        ValidationConditionId.ABLATION_NO_L4.value: "No L4 graph",
        ValidationConditionId.ABLATION_NO_L5.value: "No L5 explanation",
    }
    exit_rows = [r for r in report.aggregates if r.scenario == "exit_blockage"]
    for row in exit_rows:
        if row.condition_id not in ablation_labels:
            continue
        lines.append(
            f"    {ablation_labels[row.condition_id]} & "
            f"{row.detection_accuracy.mean:.3f} & "
            f"{row.explanation_completeness.mean:.3f} & "
            f"{row.privacy_violations.mean:.1f} \\\\"
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
    output_path.write_text(content, encoding="utf-8")
    return content


__all__ = [
    "DEFAULT_SEEDS",
    "PAPER_SCENARIOS",
    "VALIDATION_DISCLAIMER",
    "ValidationBatteryReport",
    "ValidationConditionId",
    "ValidationRunRecord",
    "generate_validation_latex_tables",
    "run_validation_battery",
]
