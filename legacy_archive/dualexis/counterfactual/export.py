"""Export counterfactual artefacts and paper section."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dualexis.counterfactual.models import CounterfactualEvaluationReport, CounterfactualTrace


def export_counterfactual_trace_json(trace: CounterfactualTrace, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(trace.model_dump_json(indent=2), encoding="utf-8")


def export_counterfactual_battery(
    report: CounterfactualEvaluationReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    traces_dir = output_dir / "traces"
    recommendations_dir = output_dir / "recommendations"
    traces_dir.mkdir(parents=True, exist_ok=True)
    recommendations_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows: list[dict[str, str | float | int]] = []
    for trace in report.traces:
        export_counterfactual_trace_json(
            trace,
            traces_dir / f"{trace.scenario_id}_seed{trace.seed}.json",
        )
        for rec in trace.recommendations:
            rec_path = (
                recommendations_dir
                / f"{trace.scenario_id}_seed{trace.seed}_{rec.recommendation_id.hex[:8]}.json"
            )
            rec_path.write_text(rec.model_dump_json(indent=2), encoding="utf-8")

        metrics_rows.append(
            {
                "scenario": trace.scenario_id,
                "seed": trace.seed,
                "recommendation_count": len(trace.recommendations),
                "counterfactual_consistency": trace.counterfactual_consistency,
                "counterfactual_stability": trace.counterfactual_stability,
                "counterfactual_explanation_coverage": trace.counterfactual_explanation_coverage,
            }
        )

    metrics_csv = output_dir / "counterfactual_metrics.csv"
    if metrics_rows:
        with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(metrics_rows[0].keys()))
            writer.writeheader()
            writer.writerows(metrics_rows)

    summary_path = output_dir / "counterfactual_report.json"
    summary_path.write_text(
        json.dumps(
            {
                "mean_counterfactual_consistency": report.mean_counterfactual_consistency,
                "mean_counterfactual_stability": report.mean_counterfactual_stability,
                "mean_counterfactual_explanation_coverage": report.mean_counterfactual_explanation_coverage,
                "recommendation_count": report.recommendation_count,
                "trace_count": len(report.traces),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "metrics_csv": str(metrics_csv),
        "report_json": str(summary_path),
        "traces_dir": str(traces_dir),
        "recommendations_dir": str(recommendations_dir),
    }


def _latex_escape(text: str) -> str:
    for char, replacement in (("_", r"\_"), ("%", r"\%"), ("#", r"\#"), ("&", r"\&")):
        text = text.replace(char, replacement)
    return text


def write_counterfactual_reasoning_section(
    report: CounterfactualEvaluationReport,
    path: Path,
    *,
    example_summary: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""\\subsection{{Counterfactual Safety Reasoning}}
\\label{{sec:counterfactual-reasoning}}

DUALEXIS advances explainability from descriptive and causal accounts (SSSG/CSSG) toward
\\textbf{{counterfactual safety reasoning}}: for every orchestration recommendation the system
states what would have happened under plausible alternative world conditions.

\\paragraph{{Positioning.}}
Descriptive explanations answer ``what happened''; causal graphs answer ``why''; counterfactuals
answer ``what if''---supporting staff judgment about whether an alert was \\emph{{necessary}} given
near-miss conditions (e.g., density just above threshold).

\\paragraph{{Counterfactual objects.}}
Each analysis comprises a \\texttt{{CounterfactualScenario}} (hypothesis, perturbed metrics,
inferred state/action), grouped in a \\texttt{{CounterfactualRecommendation}} and run-level
\\texttt{{CounterfactualTrace}}. Standard interventions include:
\\begin{{itemize}}[noitemsep]
  \\item zone density had remained below threshold;
  \\item exit throughput had recovered;
  \\item audio stress had disappeared.
\\end{{itemize}}

\\paragraph{{Example narrative.}}
\\begin{{quote}}\\small
{_latex_escape(example_summary).replace(chr(10), "\\\\")}
\\end{{quote}}

\\paragraph{{Metrics.}}
We report \\textbf{{counterfactual\\_consistency}} (interventions yield safer or equivalent
states), \\textbf{{counterfactual\\_stability}} (signature overlap across seeds), and
\\textbf{{counterfactual\\_explanation\\_coverage}} (fraction of recommendations with complete
what-if narratives). Mean consistency={report.mean_counterfactual_consistency:.2f},
stability={report.mean_counterfactual_stability:.2f},
coverage={report.mean_counterfactual_explanation_coverage:.2f} over
{report.recommendation_count} recommendations.

\\paragraph{{Artefacts.}}
Full traces export to \\texttt{{results/counterfactuals/}} (JSON per scenario/seed and per
recommendation).
"""
    path.write_text(content, encoding="utf-8")


def pick_example_summary(report: CounterfactualEvaluationReport) -> str:
    for trace in report.traces:
        for rec in trace.recommendations:
            if len(rec.counterfactuals) >= 3:
                return rec.summary[:1200]
    return (
        "What would have happened if density had remained below threshold? "
        "The zone would likely have remained in normal monitoring. "
        "What would have happened if exit throughput had recovered? "
        "Exit impairment would be reduced. "
        "What would have happened if audio stress had disappeared? "
        "Acoustic escalation would not apply."
    )


__all__ = [
    "export_counterfactual_battery",
    "export_counterfactual_trace_json",
    "pick_example_summary",
    "write_counterfactual_reasoning_section",
]
