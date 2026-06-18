"""Run audit tasks against exported trace formats."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dualexis.evaluation.audit_tasks.gold_generator import (
    generate_task_gold,
    gold_for_missing_disposition_mutation,
    gold_for_privacy_mutation,
    gold_for_removed_evidence_link,
    gold_for_removed_leakage_metadata,
    gold_for_reordered_governance,
    MUTATION_FORBIDDEN_KEY,
)
from dualexis.evaluation.audit_tasks.metrics import (
    completeness_score,
    information_loss_ratio,
    mean_query_hops,
    query_success_rate,
    violation_detection_metrics,
)
from dualexis.evaluation.audit_tasks.models import (
    AuditTaskId,
    AuditTaskKind,
    TaskEvalResult,
    TaskGold,
)
from dualexis.evaluation.audit_tasks.mutations import apply_mutation
from dualexis.evaluation.audit_tasks.queries import evaluate_task
from dualexis.evaluation.audit_tasks.task_registry import AUDIT_TASKS, AuditTaskSpec, MUTATION_TASKS
from dualexis.evaluation.exporters.models import AuditTraceExports, ExportFormat
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.tsgg.models import TsggRunRecord


@dataclass(frozen=True)
class FormatTaskMetrics:
    export_format: ExportFormat
    query_success_rate: float
    mean_completeness: float
    mean_information_loss: float
    mean_query_hops: float
    violation_f1: float


@dataclass(frozen=True)
class RunAuditReport:
    scenario_id: str
    seed: int
    clean_results: tuple[TaskEvalResult, ...]
    mutation_results: tuple[TaskEvalResult, ...]


def run_audit_tasks_for_exports(
    exports: AuditTraceExports,
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> RunAuditReport:
    """Evaluate clean and mutated audit tasks across all export formats."""
    gold_map = generate_task_gold(record, leakage_report=leakage_report)
    clean_results: list[TaskEvalResult] = []
    mutation_results: list[TaskEvalResult] = []

    for task in AUDIT_TASKS:
        gold = gold_map[task.task_id]
        for export_format in ExportFormat:
            payload = exports.payload(export_format)
            clean_results.append(evaluate_task(task.task_id, export_format, payload, gold))

    for task in MUTATION_TASKS:
        mutation_gold = _mutation_gold(task, record, gold_map)
        for export_format in ExportFormat:
            payload = apply_mutation(exports.payload(export_format), export_format, task.mutation or "")
            mutation_results.append(
                evaluate_task(task.task_id, export_format, payload, mutation_gold)
            )

    return RunAuditReport(
        scenario_id=exports.scenario_id,
        seed=exports.seed,
        clean_results=tuple(clean_results),
        mutation_results=tuple(mutation_results),
    )


def aggregate_format_metrics(
    reports: list[RunAuditReport],
    gold_by_run: dict[tuple[str, int], dict[AuditTaskId, TaskGold]],
) -> dict[ExportFormat, FormatTaskMetrics]:
    aggregates: dict[ExportFormat, FormatTaskMetrics] = {}
    for export_format in ExportFormat:
        clean = [
            result
            for report in reports
            for result in report.clean_results
            if result.export_format == export_format.value
        ]
        gold_lookup = gold_by_run
        completeness_values = []
        loss_values = []
        for report in reports:
            for result in report.clean_results:
                if result.export_format != export_format.value:
                    continue
                gold = gold_lookup[(report.scenario_id, report.seed)][result.task_id]
                completeness_values.append(completeness_score(result, gold))
                loss_values.append(information_loss_ratio(result, gold))

        violation_f1_values = []
        violation_tasks = {
            task.task_id for task in MUTATION_TASKS if task.kind == AuditTaskKind.VIOLATION_DETECTION
        }
        for report in reports:
            for result in report.mutation_results:
                if (
                    result.export_format != export_format.value
                    or result.task_id not in violation_tasks
                    or not result.applicable
                ):
                    continue
                expected_positive = True
                predicted_positive = bool(result.success)
                violation_f1_values.append(
                    violation_detection_metrics(
                        predicted_positive=predicted_positive,
                        expected_positive=expected_positive,
                    ).f1
                )

        aggregates[export_format] = FormatTaskMetrics(
            export_format=export_format,
            query_success_rate=query_success_rate(clean),
            mean_completeness=round(
                sum(completeness_values) / len(completeness_values) if completeness_values else 1.0,
                4,
            ),
            mean_information_loss=round(
                sum(loss_values) / len(loss_values) if loss_values else 0.0,
                4,
            ),
            mean_query_hops=mean_query_hops(clean),
            violation_f1=round(
                sum(violation_f1_values) / len(violation_f1_values) if violation_f1_values else 0.0,
                4,
            ),
        )
    return aggregates


def _mutation_gold(
    task: AuditTaskSpec,
    record: TsggRunRecord,
    gold_map: dict[AuditTaskId, TaskGold],
) -> TaskGold:
    if task.task_id == AuditTaskId.A2_MISSING_HUMAN_DISPOSITION:
        ids = [
            str(rec.recommendation_id)
            for rec in record.pipeline_output.recommendations
            if rec.requires_human_review
        ]
        return gold_for_missing_disposition_mutation(ids)
    if task.task_id == AuditTaskId.A3_PRIVACY_VIOLATION:
        return gold_for_privacy_mutation(MUTATION_FORBIDDEN_KEY)
    if task.task_id == AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT:
        base = gold_map[task.task_id]
        if not base.applies or not record.causal_trace.causal_transitions:
            return TaskGold(
                task_id=task.task_id,
                kind=base.kind,
                expected=None,
                applies=False,
            )
        transition_id = str(record.causal_trace.causal_transitions[0].transition_id)
        return gold_for_removed_evidence_link(transition_id)
    if task.task_id == AuditTaskId.A5_GOVERNANCE_APPEND_ONLY:
        return gold_for_reordered_governance()
    if task.task_id == AuditTaskId.A6_BENCHMARK_COUPLING:
        return gold_for_removed_leakage_metadata()
    return gold_map[task.task_id]


__all__ = [
    "FormatTaskMetrics",
    "RunAuditReport",
    "aggregate_format_metrics",
    "run_audit_tasks_for_exports",
]
