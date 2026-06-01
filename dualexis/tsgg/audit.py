"""Run full TSGG framework evaluation and export artefacts."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.leakage_audit.audit import run_leakage_audit
from dualexis.governance.formal_audit import run_formal_governance_audit
from dualexis.simulation.scenario import ScenarioId
from dualexis.tsgg.export import (
    generate_tsgg_framework_pdf,
    write_tsgg_figure_include,
    write_tsgg_framework_section,
    write_tsgg_unified_metrics_table,
)
from dualexis.tsgg.metrics import compute_tsgg_unified_metrics
from dualexis.tsgg.models import (
    TSGG_DISCLAIMER,
    TSGG_PIPELINE_CHAIN,
    TsggFrameworkReport,
)
from dualexis.tsgg.pipeline import run_tsgg_record
from dualexis.tsgg.trust_propagation import (
    export_trust_propagation_artifacts,
    propagate_trust_batch,
)

DEFAULT_SCENARIOS: tuple[str, ...] = tuple(s.value for s in ScenarioId)
PAPER_SCENARIOS: tuple[str, ...] = (
    "normal_flow",
    "exit_blockage",
    "multimodal_conflict",
    "evacuation_recommendation",
    "crowd_acceleration",
    "audio_stress_signal",
)


@dataclass(frozen=True)
class TsggBatteryReport:
    output_dir: Path
    framework_json: Path
    metrics_csv: Path
    section_tex: Path
    table_tex: Path
    figure_pdf: Path
    figure_include_tex: Path
    trust_section_tex: Path | None = None
    trust_figure_pdf: Path | None = None


def run_tsgg_framework(
    *,
    output_dir: Path,
    paper_tables: Path | None = None,
    paper_sections: Path | None = None,
    paper_figures: Path | None = None,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3),
    leakage_fast: bool = False,
) -> TsggBatteryReport:
    """Execute TSGG pipeline, leakage audit, unified metrics, and paper export."""
    output_dir.mkdir(parents=True, exist_ok=True)
    leakage_dir = output_dir / "leakage"
    leakage_report = run_leakage_audit(
        output_dir=leakage_dir,
        scenarios=scenarios,
        fast=leakage_fast,
    )

    formal_audit = run_formal_governance_audit(fast=leakage_fast)
    records = [run_tsgg_record(scenario, seed=seed) for scenario in scenarios for seed in seeds]
    unified = compute_tsgg_unified_metrics(
        records,
        leakage_report,
        formal_metrics=formal_audit.metrics,
    )

    report = TsggFrameworkReport(
        generated_at=datetime.now(tz=UTC),
        pipeline_stages=TSGG_PIPELINE_CHAIN,
        run_records=tuple(records),
        unified_metrics=unified,
        leakage_audit=leakage_report,
        disclaimer=TSGG_DISCLAIMER,
    )

    framework_json = output_dir / "tsgg_framework_report.json"
    payload = report.model_dump(mode="json")
    payload["generated_at"] = report.generated_at.isoformat()
    framework_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    metrics_csv = output_dir / "tsgg_unified_metrics.csv"
    with metrics_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(unified.model_dump().keys()))
        writer.writeheader()
        writer.writerow(unified.model_dump())

    traces_dir = output_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        name = f"{record.scenario_id}_seed{record.seed}.json"
        trace_payload = {
            "scenario_id": record.scenario_id,
            "seed": record.seed,
            "stage_counts": record.stage_counts,
            "causal_transitions": len(record.causal_trace.causal_transitions),
            "recommendations": len(record.pipeline_output.recommendations),
            "governance_traces": len(record.governance_traces),
        }
        (traces_dir / name).write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")

    tables_dir = paper_tables or Path("results_reference/tables")
    sections_dir = paper_sections or Path("results_reference/sections")
    figures_dir = paper_figures or Path("results_reference/figures")

    table_tex = tables_dir / "tsgg_unified_metrics.tex"
    section_tex = sections_dir / "tsgg_framework.tex"
    figure_pdf = figures_dir / "tsgg_framework.pdf"
    figure_include = sections_dir / "tsgg_figure.tex"

    write_tsgg_unified_metrics_table(unified, table_tex)
    write_tsgg_framework_section(report, section_tex)
    generate_tsgg_framework_pdf(figure_pdf)
    write_tsgg_figure_include(figure_include)

    trust_report = propagate_trust_batch(records, leakage=leakage_report)
    trust_paths = export_trust_propagation_artifacts(
        trust_report,
        output_dir / "trust",
        paper_sections=sections_dir,
        paper_tables=tables_dir,
        paper_figures=figures_dir,
    )

    return TsggBatteryReport(
        output_dir=output_dir,
        framework_json=framework_json,
        metrics_csv=metrics_csv,
        section_tex=section_tex,
        table_tex=table_tex,
        figure_pdf=figure_pdf,
        figure_include_tex=figure_include,
        trust_section_tex=Path(trust_paths["section_tex"]),
        trust_figure_pdf=Path(trust_paths["figure_pdf"]),
    )


__all__ = ["TsggBatteryReport", "run_tsgg_framework"]
