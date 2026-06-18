"""Unit tests for audit-task runner and metrics."""

from __future__ import annotations

import pytest

from dualexis.evaluation.audit_tasks.gold_generator import generate_task_gold
from dualexis.evaluation.audit_tasks.models import AuditTaskId
from dualexis.evaluation.audit_tasks.runner import aggregate_format_metrics, run_audit_tasks_for_exports
from dualexis.evaluation.exporters import ExportFormat, build_audit_trace_exports
from dualexis.leakage_audit.audit import run_leakage_audit
from dualexis.tsgg.pipeline import run_tsgg_record


@pytest.fixture
def tmp_leakage(tmp_path):
    def _run(scenario: str):
        return run_leakage_audit(
            output_dir=tmp_path / "leakage",
            scenarios=(scenario,),
            fast=True,
        )

    return _run


@pytest.mark.unit
def test_run_audit_tasks_for_exports_clean_success(tmp_leakage) -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    leakage = tmp_leakage("exit_blockage")
    exports = build_audit_trace_exports(record, leakage_report=leakage)
    report = run_audit_tasks_for_exports(exports, record, leakage_report=leakage)
    assert report.clean_results
    tsgg_a6 = next(
        result
        for result in report.clean_results
        if result.task_id == AuditTaskId.A6_BENCHMARK_COUPLING
        and result.export_format == ExportFormat.TSGG.value
    )
    assert tsgg_a6.success


@pytest.mark.unit
def test_mutation_tasks_flag_violations_on_flat_json() -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    exports = build_audit_trace_exports(record)
    report = run_audit_tasks_for_exports(exports, record)
    privacy = next(
        result
        for result in report.mutation_results
        if result.task_id == AuditTaskId.A3_PRIVACY_VIOLATION
        and result.export_format == ExportFormat.FLAT_JSON.value
    )
    assert privacy.success


@pytest.mark.unit
def test_aggregate_format_metrics_prefers_tsgg_query_success(tmp_leakage) -> None:
    record = run_tsgg_record("evacuation_recommendation", seed=1)
    leakage = tmp_leakage("evacuation_recommendation")
    exports = build_audit_trace_exports(record, leakage_report=leakage)
    report = run_audit_tasks_for_exports(exports, record, leakage_report=leakage)
    gold = {(record.scenario_id, record.seed): generate_task_gold(record, leakage_report=leakage)}
    metrics = aggregate_format_metrics([report], gold)
    assert metrics[ExportFormat.TSGG].query_success_rate >= metrics[ExportFormat.FLAT_JSON].query_success_rate
