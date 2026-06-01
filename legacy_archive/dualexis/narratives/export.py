"""Export longitudinal narrative artefacts and paper section."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from dualexis.narratives.generator import NarrativeGenerator
from dualexis.narratives.metrics import aggregate_trace_metrics
from dualexis.narratives.models import (
    NARRATIVE_DISCLAIMER,
    LongitudinalNarrativeReport,
    NarrativeTrace,
)
from dualexis.tsgg.audit import PAPER_SCENARIOS
from dualexis.tsgg.models import TsggRunRecord
from dualexis.tsgg.pipeline import run_tsgg_record


def build_longitudinal_report(
    records: list[TsggRunRecord],
    *,
    generator: NarrativeGenerator | None = None,
) -> LongitudinalNarrativeReport:
    """Generate narrative traces for all records (primary zone per run)."""
    gen = generator or NarrativeGenerator()
    traces: list[NarrativeTrace] = []
    for record in records:
        traces.append(gen.generate_primary(record))
    completeness, consistency, fidelity = aggregate_trace_metrics(traces)
    return LongitudinalNarrativeReport(
        generated_at=datetime.now(tz=UTC),
        traces=tuple(traces),
        mean_completeness=completeness,
        mean_consistency=consistency,
        mean_fidelity=fidelity,
        disclaimer=NARRATIVE_DISCLAIMER,
    )


def export_longitudinal_narratives(
    report: LongitudinalNarrativeReport,
    output_dir: Path,
    *,
    paper_sections: Path | None = None,
) -> dict[str, str]:
    """Write JSON, per-scenario text timelines, CSV metrics, and LaTeX section."""
    output_dir.mkdir(parents=True, exist_ok=True)

    report_json = output_dir / "longitudinal_narratives_report.json"
    payload = report.model_dump(mode="json")
    payload["generated_at"] = report.generated_at.isoformat()
    report_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    narratives_dir = output_dir / "timelines"
    narratives_dir.mkdir(parents=True, exist_ok=True)
    for trace in report.traces:
        name = f"{trace.scenario_id}_seed{trace.seed}_{trace.zone_id}.txt"
        (narratives_dir / name).write_text(trace.rendered_text + "\n", encoding="utf-8")

    metrics_csv = output_dir / "narrative_metrics.csv"
    with metrics_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario_id",
                "seed",
                "zone_id",
                "narrative_completeness",
                "narrative_consistency",
                "narrative_fidelity",
                "beat_count",
            ],
        )
        writer.writeheader()
        for trace in report.traces:
            writer.writerow(
                {
                    "scenario_id": trace.scenario_id,
                    "seed": trace.seed,
                    "zone_id": trace.zone_id,
                    "narrative_completeness": trace.metrics.narrative_completeness,
                    "narrative_consistency": trace.metrics.narrative_consistency,
                    "narrative_fidelity": trace.metrics.narrative_fidelity,
                    "beat_count": len(trace.beats),
                }
            )

    summary_json = output_dir / "narrative_summary.json"
    summary_json.write_text(
        json.dumps(
            {
                "mean_completeness": report.mean_completeness,
                "mean_consistency": report.mean_consistency,
                "mean_fidelity": report.mean_fidelity,
                "trace_count": len(report.traces),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    paths = {
        "report_json": str(report_json),
        "metrics_csv": str(metrics_csv),
        "summary_json": str(summary_json),
        "timelines_dir": str(narratives_dir),
    }

    if paper_sections is not None:
        section_path = paper_sections / "longitudinal_explanations.tex"
        write_longitudinal_explanations_section(report, section_path)
        paths["section_tex"] = str(section_path)

    return paths


def run_longitudinal_narratives(
    *,
    output_dir: Path,
    paper_sections: Path | None = None,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3),
) -> LongitudinalNarrativeReport:
    """Run TSGG and export longitudinal narratives."""
    records = [run_tsgg_record(scenario, seed=seed) for scenario in scenarios for seed in seeds]
    report = build_longitudinal_report(records)
    export_longitudinal_narratives(report, output_dir, paper_sections=paper_sections)
    return report


def _tex_escape(value: str) -> str:
    return value.replace("_", r"\_")


def write_longitudinal_explanations_section(
    report: LongitudinalNarrativeReport,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    example = report.traces[0] if report.traces else None
    example_block = ""
    if example is not None:
        lines = example.rendered_text.split("\n")
        formatted = "\n".join(
            f"  \\texttt{{{lines[i]}}} & \\textit{{{_tex_escape(lines[i + 1])}}}"
            for i in range(0, len(lines) - 1, 2)
            if i + 1 < len(lines)
        )
        zone_tex = example.zone_id.replace("_", r"\_")
        scenario_tex = example.scenario_id.replace("_", r"\_")
        example_block = f"""
\\paragraph{{Illustrative timeline (scenario \\texttt{{{scenario_tex}}}, zone \\texttt{{{zone_tex}}}).}}
\\begin{{tabular}}{{@{{}}ll@{{}}}}
\\toprule
Time & Event \\\\
\\midrule
{formatted} \\\\
\\bottomrule
\\end{{tabular}}
"""

    content = f"""\\section{{Longitudinal safety narratives}}
\\label{{sec:longitudinal-narratives}}

DUALEXIS explains the \\textbf{{evolution}} of confined-space safety situations through
\\emph{{longitudinal narratives}} derived from full TSGG traces:
evidence $\\rightarrow$ state $\\rightarrow$ recommendation $\\rightarrow$ governance.
Each \\texttt{{NarrativeTrace}} is a time-ordered sequence of beats, avoiding isolated
decision snapshots.

\\paragraph{{Generator.}}
The \\texttt{{NarrativeGenerator}} walks TSGG artefacts per zone, emitting clock-labelled
lines (e.g., \\texttt{{08:04}}) for indicator changes, state transitions, review escalation,
operator disposition, and stabilization.

\\paragraph{{Metrics.}}
\\begin{{itemize}}[noitemsep]
  \\item \\textbf{{narrative\\_completeness}} (mean ${report.mean_completeness:.3f}$) ---
        coverage of evidence, state, recommendation, and governance stages;
  \\item \\textbf{{narrative\\_consistency}} (mean ${report.mean_consistency:.3f}$) ---
        monotonic timeline and allowed safety-state transitions;
  \\item \\textbf{{narrative\\_fidelity}} (mean ${report.mean_fidelity:.3f}$) ---
        alignment between narrative text and underlying TSGG records.
\\end{{itemize}}

{example_block}

\\paragraph{{Positioning.}}
Longitudinal narratives operationalize TSGG for institutional sense-making: operators and
auditors review \\emph{{how}} a situation unfolded, not only the terminal recommendation.
Synthetic harness only; {report.disclaimer}
"""
    path.write_text(content, encoding="utf-8")


__all__ = [
    "build_longitudinal_report",
    "export_longitudinal_narratives",
    "run_longitudinal_narratives",
    "write_longitudinal_explanations_section",
]
