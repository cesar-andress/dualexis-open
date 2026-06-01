"""Export ontology drift artefacts and paper section."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dualexis.ontology_drift.detection import persist_version_vocabulary
from dualexis.ontology_drift.models import OntologyDriftReport


def export_ontology_drift_report(
    report: OntologyDriftReport,
    output_dir: Path,
    *,
    paper_sections: Path | None = None,
    registry_dir: Path | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "ontology_drift_report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    scenario_rows = [
        {
            "scenario": row.scenario_id,
            "version": row.version,
            "ontology_stability": row.ontology_stability,
            "semantic_drift": row.semantic_drift,
            "recommendation_drift": row.recommendation_drift,
            "safety_state_drift": row.safety_state_drift,
        }
        for row in report.per_scenario
    ]
    scenario_csv = output_dir / "scenario_drift.csv"
    if scenario_rows:
        with scenario_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(scenario_rows[0].keys()))
            writer.writeheader()
            writer.writerows(scenario_rows)

    metrics_csv = output_dir / "aggregate_metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ontology_stability",
                "semantic_drift",
                "recommendation_drift",
                "cross_version_semantic_drift",
                "seed_count",
                "scenario_count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "ontology_stability": report.ontology_stability,
                "semantic_drift": report.semantic_drift,
                "recommendation_drift": report.recommendation_drift,
                "cross_version_semantic_drift": report.cross_version_semantic_drift,
                "seed_count": len(report.seeds),
                "scenario_count": len(report.scenarios),
            }
        )

    version_rows = [
        {
            "version": summary.version,
            "semantic_label_count": len(summary.semantic_labels),
            "safety_state_count": len(summary.safety_states),
            "recommendation_count": len(summary.recommendations),
            "snapshot_count": summary.snapshot_count,
        }
        for summary in report.version_summaries
    ]
    version_csv = output_dir / "version_vocabularies.csv"
    with version_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(version_rows[0].keys()))
        writer.writeheader()
        writer.writerows(version_rows)

    snapshots_dir = output_dir / "snapshots"
    snapshots_dir.mkdir(exist_ok=True)
    for snap in report.snapshots:
        path = snapshots_dir / f"{snap.scenario_id}_seed{snap.seed}_v{snap.version}.json"
        path.write_text(snap.model_dump_json(indent=2), encoding="utf-8")

    reg_dir = registry_dir or output_dir / "registry"
    persist_version_vocabulary(report, reg_dir)

    paths = {
        "report_json": str(report_path),
        "scenario_csv": str(scenario_csv),
        "metrics_csv": str(metrics_csv),
        "version_csv": str(version_csv),
        "registry_dir": str(reg_dir),
    }

    if paper_sections is not None:
        section_path = paper_sections / "ontology_drift.tex"
        write_ontology_drift_section(report, section_path)
        paths["section_tex"] = str(section_path)

    summary_path = output_dir / "ontology_drift_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "ontology_stability": report.ontology_stability,
                "semantic_drift": report.semantic_drift,
                "recommendation_drift": report.recommendation_drift,
                "cross_version_semantic_drift": report.cross_version_semantic_drift,
                "versions": list(report.versions),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    paths["summary_json"] = str(summary_path)

    return paths


def write_ontology_drift_section(report: OntologyDriftReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scenario_lines = []
    for row in report.per_scenario:
        scen = row.scenario_id.replace("_", r"\_")
        scenario_lines.append(
            f"    {scen} & {row.ontology_stability:.2f} & {row.semantic_drift:.2f} & "
            f"{row.recommendation_drift:.2f} \\\\"
        )

    version_lines = []
    for summary in report.version_summaries:
        version_lines.append(
            f"    {summary.version} & {len(summary.semantic_labels)} & "
            f"{len(summary.safety_states)} & {len(summary.recommendations)} \\\\"
        )

    content = f"""\\subsection{{Ontology Drift Detection}}
\\label{{sec:ontology-drift}}

Benchmark evolution can silently alter the \\textbf{{semantic contract}} of a decision-support
system even when detection accuracy appears stable. DUALEXIS implements \\textbf{{ontology drift
detection}} to track whether meaning remains consistent across scenarios, RNG seeds, and
package versions.

\\paragraph{{Tracked layers.}}
\\begin{{itemize}}[noitemsep]
  \\item \\textbf{{Semantic labels}} --- independent GT labels, event categories, and published
        semantic event types;
  \\item \\textbf{{Safety states}} --- SSSG state vocabulary and transition endpoints;
  \\item \\textbf{{Recommendations}} --- orchestration actions and severities per zone.
\\end{{itemize}}

\\paragraph{{Audit dimensions.}}
Snapshots are collected for each $(\\mathrm{{scenario}}, \\mathrm{{seed}}, \\mathrm{{version}})$
cell. We measure pairwise Jaccard instability across seeds (drift) and aggregate vocabularies per
version for cross-release comparison. Registry files under \\texttt{{results/ontology\\_drift/registry/}}
enable drift audits between successive benchmark versions.

\\paragraph{{Metrics.}}
\\textbf{{ontology\\_stability}} $={report.ontology_stability:.3f}$ (higher is better),
\\textbf{{semantic\\_drift}} $={report.semantic_drift:.3f}$,
\\textbf{{recommendation\\_drift}} $={report.recommendation_drift:.3f}$.
Cross-version semantic drift $={report.cross_version_semantic_drift:.3f}$ compares aggregate
label vocabularies between registered releases ($N={len(report.seeds)}$ seeds,
{len(report.scenarios)} scenarios).

\\begin{{table}}[htbp]
  \\centering
  \\caption{{Per-scenario ontology stability and drift (current version).}}
  \\label{{tab:ontology-drift-scenario}}
  \\small
  \\begin{{tabular}}{{@{{}}lrrr@{{}}}}
    \\toprule
    Scenario & Stability & Semantic drift & Recommendation drift \\\\
    \\midrule
{chr(10).join(scenario_lines)}
    \\bottomrule
  \\end{{tabular}}
\\end{{table}}

\\begin{{table}}[htbp]
  \\centering
  \\caption{{Aggregate ontology vocabulary by benchmark version.}}
  \\label{{tab:ontology-version-vocab}}
  \\small
  \\begin{{tabular}}{{@{{}}lrrr@{{}}}}
    \\toprule
    Version & \\# labels & \\# states & \\# recommendations \\\\
    \\midrule
{chr(10).join(version_lines)}
    \\bottomrule
  \\end{{tabular}}
\\end{{table}}

\\paragraph{{Interpretation.}}
Low drift across seeds supports that stochastic world dynamics do not fragment the benchmark
ontology; elevated recommendation drift flags orchestration sensitivity worth pre-registering
before field pilots. This evaluation answers whether \\emph{{semantic meaning remains stable}}
as the harness evolves---a prerequisite for comparable Stage~S2a human-factors studies.
"""
    path.write_text(content, encoding="utf-8")


__all__ = ["export_ontology_drift_report", "write_ontology_drift_section"]
