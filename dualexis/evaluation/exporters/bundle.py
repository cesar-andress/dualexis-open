"""Build all audit-comparison exports from one TSGG run record."""

from __future__ import annotations

from dualexis.evaluation.exporters.flat_json_exporter import export_flat_json_log
from dualexis.evaluation.exporters.models import AuditTraceExports
from dualexis.evaluation.exporters.prov_exporter import export_prov_document
from dualexis.evaluation.exporters.tsgg_native_exporter import export_tsgg_native
from dualexis.evaluation.exporters.xes_exporter import export_xes_log
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.tsgg.models import TsggRunRecord


def build_audit_trace_exports(
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> AuditTraceExports:
    """Produce TSGG, flat JSON, PROV, and XES exports from the same underlying run."""
    return AuditTraceExports(
        scenario_id=record.scenario_id,
        seed=record.seed,
        tsgg=export_tsgg_native(record, leakage_report=leakage_report),
        flat_json=export_flat_json_log(record, leakage_report=leakage_report),
        prov=export_prov_document(record, leakage_report=leakage_report),
        xes=export_xes_log(record, leakage_report=leakage_report),
    )


__all__ = ["build_audit_trace_exports"]
