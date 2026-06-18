"""Audit-comparison battery: TSGG vs flat JSON vs PROV vs XES trace auditability."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.evaluation.audit_tasks.models import AuditTaskId
from dualexis.evaluation.audit_tasks.runner import (
    FormatTaskMetrics,
    RunAuditReport,
    aggregate_format_metrics,
    run_audit_tasks_for_exports,
)
from dualexis.evaluation.exporters.bundle import build_audit_trace_exports
from dualexis.evaluation.exporters.models import ExportFormat, PRIMARY_AUDIT_FORMATS
from dualexis.experiments.empirical_battery import DEFAULT_SEEDS, PAPER_SCENARIOS
from dualexis.leakage_audit.audit import run_leakage_audit
from dualexis.tsgg.pipeline import run_tsgg_record

AUDIT_COMPARISON_DISCLAIMER = (
    "Post-hoc trace auditability comparison on synthetic validation harness. "
    "Reports query success, completeness, information loss, and violation-detection F1 "
    "for export formats derived from the same underlying run record. "
    "Not operational safety, detector accuracy, or human outcome claims."
)


@dataclass(frozen=True)
class AuditComparisonReport:
    generated_at: datetime
    scenarios: tuple[str, ...]
    seeds: tuple[int, ...]
    run_count: int
    leakage_score: float
    format_metrics: dict[str, FormatTaskMetrics]
    disclaimer: str


def run_audit_comparison_battery(
    *,
    output_dir: Path,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    leakage_fast: bool = True,
) -> AuditComparisonReport:
    """Run 6×N audit comparison and export CSV/JSON/LaTeX artefacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    leakage = run_leakage_audit(
        output_dir=output_dir / "leakage",
        scenarios=scenarios,
        fast=leakage_fast,
    )

    reports: list[RunAuditReport] = []
    gold_by_run: dict[tuple[str, int], dict[AuditTaskId, object]] = {}
    export_rows: list[dict[str, object]] = []

    for scenario in scenarios:
        for seed in seeds:
            record = run_tsgg_record(scenario, seed=seed)
            exports = build_audit_trace_exports(record, leakage_report=leakage)
            run_report = run_audit_tasks_for_exports(
                exports,
                record,
                leakage_report=leakage,
            )
            reports.append(run_report)
            from dualexis.evaluation.audit_tasks.gold_generator import generate_task_gold

            gold_by_run[(scenario, seed)] = generate_task_gold(record, leakage_report=leakage)

            for export_format in ExportFormat:
                export_path = (
                    output_dir
                    / ("exports" if export_format in PRIMARY_AUDIT_FORMATS else "exports_supplementary")
                    / export_format.value
                    / f"{scenario}_seed{seed}.json"
                )
                export_path.parent.mkdir(parents=True, exist_ok=True)
                export_path.write_text(
                    json.dumps(exports.payload(export_format), indent=2, default=str),
                    encoding="utf-8",
                )

            for result in run_report.clean_results + run_report.mutation_results:
                export_rows.append(
                    {
                        "scenario": scenario,
                        "seed": seed,
                        "task_id": result.task_id.value,
                        "export_format": result.export_format,
                        "mutated": result in run_report.mutation_results,
                        "applicable": result.applicable,
                        "success": result.success,
                        "query_hops": result.query_hops,
                    }
                )

    format_metrics = aggregate_format_metrics(reports, gold_by_run)
    primary_metrics = {fmt: format_metrics[fmt] for fmt in PRIMARY_AUDIT_FORMATS}
    report = AuditComparisonReport(
        generated_at=datetime.now(tz=UTC),
        scenarios=scenarios,
        seeds=seeds,
        run_count=len(reports),
        leakage_score=leakage.leakage_score,
        format_metrics={key.value: value for key, value in primary_metrics.items()},
        disclaimer=AUDIT_COMPARISON_DISCLAIMER,
    )

    _write_csv(output_dir / "audit_comparison_results.csv", primary_metrics)
    _write_task_csv(output_dir / "audit_task_results.csv", export_rows)
    _write_json(output_dir / "audit_comparison_summary.json", report, primary_metrics)
    _write_latex(output_dir / "audit_comparison.tex", report, primary_metrics)
    return report


def _write_csv(path: Path, format_metrics: dict[ExportFormat, FormatTaskMetrics]) -> None:
    fieldnames = [
        "export_format",
        "query_success_rate",
        "mean_completeness",
        "mean_information_loss",
        "mean_query_hops",
        "violation_f1",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for export_format, metrics in format_metrics.items():
            writer.writerow(
                {
                    "export_format": export_format.value,
                    "query_success_rate": metrics.query_success_rate,
                    "mean_completeness": metrics.mean_completeness,
                    "mean_information_loss": metrics.mean_information_loss,
                    "mean_query_hops": metrics.mean_query_hops,
                    "violation_f1": metrics.violation_f1,
                }
            )


def _write_task_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(
    path: Path,
    report: AuditComparisonReport,
    format_metrics: dict[ExportFormat, FormatTaskMetrics],
) -> None:
    payload = {
        "generated_at": report.generated_at.isoformat(),
        "scenarios": list(report.scenarios),
        "seeds": list(report.seeds),
        "run_count": report.run_count,
        "leakage_score": report.leakage_score,
        "disclaimer": report.disclaimer,
        "format_metrics": {
            export_format.value: {
                "query_success_rate": metrics.query_success_rate,
                "mean_completeness": metrics.mean_completeness,
                "mean_information_loss": metrics.mean_information_loss,
                "mean_query_hops": metrics.mean_query_hops,
                "violation_f1": metrics.violation_f1,
            }
            for export_format, metrics in format_metrics.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_latex(
    path: Path,
    report: AuditComparisonReport,
    format_metrics: dict[ExportFormat, FormatTaskMetrics],
) -> None:
    lines = [
        "% Auto-generated by dualexis audit_comparison_battery.",
        "% Do not edit manually; regenerate via: experiment audit-comparison",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Post-hoc trace auditability comparison under synthetic validation "
        f"($|S|={len(report.scenarios)}$ scenarios, $N={len(report.seeds)}$ seeds). "
        "Metrics describe export-query success and information retention, not operational safety. "
        f"Reference leakage score $L_S={report.leakage_score:.3f}$ reported transparently.}}",
        "  \\label{tab:audit-comparison}",
        "  \\small",
        "  \\begin{tabular}{@{}lrrrrr@{}}",
        "    \\toprule",
        "    Format & QSR & Completeness & Info loss & Hops & Viol. F1 \\\\",
        "    \\midrule",
    ]
    labels = {
        ExportFormat.TSGG: "TSGG",
        ExportFormat.FLAT_JSON: "Flat JSON",
        ExportFormat.PROV: "PROV-JSON",
    }
    for export_format in PRIMARY_AUDIT_FORMATS:
        metrics = format_metrics[export_format]
        lines.append(
            f"    {labels[export_format]} & {metrics.query_success_rate:.3f} & "
            f"{metrics.mean_completeness:.3f} & {metrics.mean_information_loss:.3f} & "
            f"{metrics.mean_query_hops:.2f} & {metrics.violation_f1:.3f} \\\\"
        )
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def export_audit_baselines_for_run(
    record_path: Path | None,
    *,
    scenario: str,
    seed: int,
    output_dir: Path,
    leakage_fast: bool = True,
) -> Path:
    """Export all baseline formats for a single run to ``output_dir``."""
    leakage = run_leakage_audit(output_dir=output_dir / "leakage", scenarios=(scenario,), fast=leakage_fast)
    record = run_tsgg_record(scenario, seed=seed)
    exports = build_audit_trace_exports(record, leakage_report=leakage)
    output_dir.mkdir(parents=True, exist_ok=True)
    for export_format in ExportFormat:
        target = output_dir / f"{scenario}_seed{seed}_{export_format.value}.json"
        target.write_text(
            json.dumps(exports.payload(export_format), indent=2, default=str),
            encoding="utf-8",
        )
    _ = record_path
    return output_dir


__all__ = [
    "AUDIT_COMPARISON_DISCLAIMER",
    "AuditComparisonReport",
    "export_audit_baselines_for_run",
    "run_audit_comparison_battery",
]
