"""Export robustness audit artefacts and paper section."""

from __future__ import annotations

import csv
import json
import shutil
import statistics
import subprocess
from pathlib import Path

from dualexis.robustness.models import RobustnessAuditReport


def export_robustness_audit(
    report: RobustnessAuditReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "robustness_audit_report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    scenario_rows: list[dict[str, str | float | int]] = []
    for scenario in report.scenarios:
        scenario_rows.append(
            {
                "scenario": scenario.scenario_id,
                "event_stability": scenario.event_stability,
                "state_stability": scenario.state_stability,
                "recommendation_stability": scenario.recommendation_stability,
                "explanation_stability": scenario.explanation_stability,
            }
        )
    scenario_csv = output_dir / "scenario_stability.csv"
    if scenario_rows:
        with scenario_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(scenario_rows[0].keys()))
            writer.writeheader()
            writer.writerows(scenario_rows)

    dist_rows: list[dict[str, str | float]] = []
    for dist in report.aggregate_distributions:
        dist_rows.append(
            {
                "metric": dist.metric.value,
                "mean": dist.mean,
                "std": dist.std,
                "coefficient_of_variation": dist.coefficient_of_variation,
            }
        )
    dist_csv = output_dir / "aggregate_distributions.csv"
    with dist_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "mean", "std", "coefficient_of_variation"])
        writer.writeheader()
        writer.writerows(dist_rows)

    seed_rows: list[dict[str, str | float | int]] = []
    for scenario in report.scenarios:
        for seed, metrics in scenario.per_seed_vs_reference.items():
            seed_rows.append(
                {
                    "scenario": scenario.scenario_id,
                    "seed": seed,
                    **metrics,
                }
            )
    seed_csv = output_dir / "per_seed_stability.csv"
    if seed_rows:
        with seed_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(seed_rows[0].keys()))
            writer.writeheader()
            writer.writerows(seed_rows)

    summary = {
        "robustness_score_R": report.robustness_score,
        "seeds": list(report.seeds),
        "scenario_count": len(report.scenarios),
    }
    (output_dir / "robustness_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    return {
        "report_json": str(report_path),
        "scenario_csv": str(scenario_csv),
        "distributions_csv": str(dist_csv),
        "per_seed_csv": str(seed_csv),
        "summary_json": str(output_dir / "robustness_summary.json"),
    }


def aggregate_seed_series(report: RobustnessAuditReport) -> dict[str, list[tuple[int, float]]]:
    """Mean per-seed reference stability across scenarios for each metric."""
    metric_keys = ["event", "state", "recommendation", "explanation"]
    series: dict[str, list[tuple[int, float]]] = {key: [] for key in metric_keys}
    for seed in report.seeds:
        for key in metric_keys:
            values = [
                scenario.per_seed_vs_reference.get(seed, {}).get(key, 0.0)
                for scenario in report.scenarios
            ]
            series[key].append((seed, statistics.mean(values) if values else 0.0))
    return series


def write_robustness_plot_tex(
    series: dict[str, list[tuple[int, float]]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plots: list[str] = []
    colors = {
        "event": "blue",
        "state": "orange",
        "recommendation": "green",
        "explanation": "red",
    }
    for key, points in series.items():
        coords = " ".join(f"({seed},{value:.4f})" for seed, value in points)
        label = key.replace("_", " ").title()
        plots.append(f"\\addplot[{colors[key]}, mark=*] coordinates {{{coords}}};")
        plots.append(f"\\addlegendentry{{{label}}}")
    tex = f"""% Auto-generated robustness vs seed plot
\\documentclass[border=2pt]{{standalone}}
\\usepackage{{pgfplots}}
\\pgfplotsset{{compat=1.18}}
\\begin{{document}}
\\begin{{tikzpicture}}
\\begin{{axis}}[
  width=12cm,
  height=7cm,
  xlabel={{Seed}},
  ylabel={{Stability (Jaccard vs. reference seed)}},
  ymin=0, ymax=1.05,
  legend style={{at={{(0.02,0.02)}},anchor=south west, font=\\footnotesize}},
  grid=major,
  title={{Semantic stability under stochastic world dynamics}},
]
{chr(10).join(plots)}
\\end{{axis}}
\\end{{tikzpicture}}
\\end{{document}}
"""
    path.write_text(tex, encoding="utf-8")


def generate_robustness_vs_seed_pdf(
    report: RobustnessAuditReport,
    pdf_path: Path,
) -> None:
    series = aggregate_seed_series(report)
    tex_path = pdf_path.parent / "robustness_vs_seed.tex"
    write_robustness_plot_tex(series, tex_path)
    build_copy = pdf_path.parent / "robustness_vs_seed_build.tex"
    build_copy.write_text(tex_path.read_text(encoding="utf-8"), encoding="utf-8")
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        if not pdf_path.exists():
            pdf_path.write_bytes(b"% Run pdflatex on robustness_vs_seed.tex\n")
        return
    subprocess.run(
        [pdflatex, "-interaction=nonstopmode", "-halt-on-error", build_copy.name],
        cwd=pdf_path.parent,
        check=False,
        capture_output=True,
    )
    built = pdf_path.parent / "robustness_vs_seed_build.pdf"
    if built.is_file():
        built.replace(pdf_path)
    for suffix in (".aux", ".log"):
        (pdf_path.parent / f"robustness_vs_seed_build{suffix}").unlink(missing_ok=True)


def write_robustness_analysis_section(
    report: RobustnessAuditReport,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dist_table = []
    for dist in report.aggregate_distributions:
        label = dist.metric.value.replace("_", r"\_")
        dist_table.append(
            f"    {label} & {dist.mean:.3f} & {dist.std:.3f} & {dist.coefficient_of_variation:.3f} \\\\"
        )
    content = f"""\\subsection{{Multiseed Robustness Audit}}
\\label{{sec:robustness-analysis}}

We evaluate \\textbf{{semantic stability under stochastic world dynamics}} by re-running the
reference harness across $N={len(report.seeds)}$ seeds per scenario. The audit quantifies whether
events, inferred safety states, orchestration recommendations, and explanations remain
consistent when the synthetic world sampler is perturbed.

\\paragraph{{Stability metrics.}}
For each dimension we build a semantic signature per $(\\mathrm{{scenario}}, \\mathrm{{seed}})$ and
report:
\\textbf{{event stability}} (published event multiset),
\\textbf{{state stability}} (SSSG transition signature),
\\textbf{{recommendation stability}} (orchestration outputs), and
\\textbf{{explanation stability}} (hashed transition and rationale text).
Pairwise Jaccard similarity across seeds yields a scenario-level stability score; per-seed
values against the reference seed support dispersion analysis.

\\paragraph{{Dispersion and robustness score.}}
Table~\\ref{{tab:robustness-distributions}} reports the mean, standard deviation, and
coefficient of variation (CV) of per-seed reference stability aggregated across scenarios.
The composite \\textbf{{robustness score}} $R={report.robustness_score:.3f}$ combines mean
stability with a CV penalty ($R \\in [0,1]$, higher is more robust).

\\begin{{table}}[htbp]
  \\centering
  \\caption{{Aggregate stability distributions across scenarios ($N={len(report.seeds)}$ seeds).}}
  \\label{{tab:robustness-distributions}}
  \\small
  \\begin{{tabular}}{{@{{}}lrrr@{{}}}}
    \\toprule
    Metric & Mean & Std & CV \\\\
    \\midrule
{chr(10).join(dist_table)}
    \\bottomrule
  \\end{{tabular}}
\\end{{table}}

\\begin{{figure}}[htbp]
  \\centering
  \\includegraphics[width=0.92\\linewidth]{{figures/robustness_vs_seed.pdf}}
  \\caption{{Mean per-seed stability (Jaccard vs. reference seed $s_1$) averaged over scenarios.
            Robustness is evaluated on semantic artefacts, not raw sensor streams.}}
  \\label{{fig:robustness-vs-seed}}
\\end{{figure}}

\\paragraph{{Artefacts.}}
Full audit exports are available under \\texttt{{results/robustness/}} (JSON report, per-scenario
and per-seed CSV tables).
"""
    path.write_text(content, encoding="utf-8")


__all__ = [
    "aggregate_seed_series",
    "export_robustness_audit",
    "generate_robustness_vs_seed_pdf",
    "write_robustness_analysis_section",
]
