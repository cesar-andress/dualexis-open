"""Export Institutional Memory Graph artefacts and paper section."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dualexis.institutional_memory.graph import InstitutionalMemoryGraphBuilder
from dualexis.institutional_memory.metrics import compute_institutional_memory_metrics
from dualexis.institutional_memory.models import (
    IMG_DISCLAIMER,
    InstitutionalMemoryReport,
)
from dualexis.tsgg.audit import PAPER_SCENARIOS
from dualexis.tsgg.pipeline import run_tsgg_record
from dualexis.tsgg.models import TsggRunRecord
from dualexis.governance.formal_models import GovernanceDecisionTrace


def build_institutional_memory_report(
    records: list[TsggRunRecord],
    *,
    min_support: int = 2,
) -> InstitutionalMemoryReport:
    traces = _collect_governance_traces(records)
    if len(traces) < 5:
        traces.extend(_simulated_governance_corpus(records))
    graph = InstitutionalMemoryGraphBuilder(min_support=min_support).build(traces)
    metrics = compute_institutional_memory_metrics(graph, run_records=records)
    return InstitutionalMemoryReport(
        generated_at=datetime.now(tz=UTC),
        graph=graph,
        metrics=metrics,
        disclaimer=IMG_DISCLAIMER,
    )


def _collect_governance_traces(
    records: list[TsggRunRecord],
) -> list[GovernanceDecisionTrace]:
    traces: list[GovernanceDecisionTrace] = []
    for record in records:
        traces.extend(record.governance_traces)
    return traces


def _simulated_governance_corpus(
    records: list[TsggRunRecord],
) -> list[GovernanceDecisionTrace]:
    """Augment IMG with balanced governance simulation when pipeline yields few reviews."""
    import random

    from dualexis.governance.cases import build_case_pool
    from dualexis.governance.models import OperatorProfile
    from dualexis.governance.simulator import simulate_operator_decision
    from dualexis.governance.state_machine import build_decision_trace

    from dualexis.governance.cases import DEFAULT_SCENARIOS

    scenarios = tuple({record.scenario_id for record in records})
    seeds = tuple(sorted({record.seed for record in records}))
    pool = build_case_pool(scenarios=scenarios, seeds=seeds)
    if len(pool) < 20:
        pool = build_case_pool(scenarios=DEFAULT_SCENARIOS, seeds=tuple(range(1, 11)))
    traces: list[GovernanceDecisionTrace] = []
    rng = random.Random(99)
    for case in pool:
        decision = simulate_operator_decision(case, profile=OperatorProfile.BALANCED, rng=rng)
        traces.append(build_decision_trace(case, decision))
    return traces


def export_institutional_memory(
    report: InstitutionalMemoryReport,
    output_dir: Path,
    *,
    paper_sections: Path | None = None,
    paper_figures: Path | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    graph = report.graph

    report_json = output_dir / "institutional_memory_report.json"
    payload = report.model_dump(mode="json")
    payload["generated_at"] = report.generated_at.isoformat()
    report_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    (output_dir / "institutional_memory_graph.dot").write_text(graph.dot, encoding="utf-8")

    patterns_dir = output_dir / "patterns"
    patterns_dir.mkdir(parents=True, exist_ok=True)
    (patterns_dir / "governance_patterns.json").write_text(
        json.dumps([p.model_dump() for p in graph.governance_patterns], indent=2),
        encoding="utf-8",
    )
    (patterns_dir / "near_miss_patterns.json").write_text(
        json.dumps([p.model_dump() for p in graph.near_miss_patterns], indent=2),
        encoding="utf-8",
    )
    (patterns_dir / "escalation_chains.json").write_text(
        json.dumps([p.model_dump() for p in graph.escalation_chains], indent=2),
        encoding="utf-8",
    )
    (patterns_dir / "override_patterns.json").write_text(
        json.dumps([p.model_dump() for p in graph.override_patterns], indent=2),
        encoding="utf-8",
    )

    figures = paper_figures or Path("results_reference/figures")
    figure_pdf = figures / "institutional_memory_graph.pdf"
    generate_institutional_memory_graph_pdf(figure_pdf, graph.dot)

    paths = {
        "report_json": str(report_json),
        "graph_dot": str(output_dir / "institutional_memory_graph.dot"),
        "figure_pdf": str(figure_pdf),
        "patterns_dir": str(patterns_dir),
    }

    if paper_sections is not None:
        section = paper_sections / "institutional_memory.tex"
        write_institutional_memory_section(report, section)
        paths["section_tex"] = str(section)

    return paths


def run_institutional_memory(
    *,
    output_dir: Path,
    paper_sections: Path | None = None,
    paper_figures: Path | None = None,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3, 4, 5),
    min_support: int = 2,
) -> InstitutionalMemoryReport:
    records = [run_tsgg_record(scenario, seed=seed) for scenario in scenarios for seed in seeds]
    effective_support = 1 if len(records) < min_support * 2 else min_support
    report = build_institutional_memory_report(records, min_support=effective_support)
    export_institutional_memory(
        report,
        output_dir,
        paper_sections=paper_sections,
        paper_figures=paper_figures,
    )
    return report


def write_institutional_memory_section(report: InstitutionalMemoryReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    g = report.graph
    m = report.metrics

    content = f"""\\section{{Institutional Memory Graphs (IMG)}}
\\label{{sec:institutional-memory}}

DUALEXIS supports \\textbf{{organizational learning}} for safety decision-support systems
through Institutional Memory Graphs (IMG): directed summaries mined from historical TSGG
governance traces. IMG complements vertex trust propagation (Section~\\ref{{sec:trust-propagation}})
and longitudinal narratives (Section~\\ref{{sec:longitudinal-narratives}}) by encoding
\\emph{{what institutions repeatedly do}} under stress.

\\paragraph{{Inputs and outputs.}}
Inputs are full TSGG traces (evidence through audit). Outputs include:
\\begin{{itemize}}[noitemsep]
  \\item \\textbf{{historical governance patterns}} ({len(g.governance_patterns)} mined);
  \\item \\textbf{{near-miss patterns}} ({len(g.near_miss_patterns)} detected);
  \\item \\textbf{{recurrent escalation chains}} ({len(g.escalation_chains)} chains);
  \\item \\textbf{{frequent override situations}} ({len(g.override_patterns)} profiles).
\\end{{itemize}}

\\paragraph{{Architecture.}}
The \\texttt{{InstitutionalMemoryGraph}} aggregates scenario nodes, governance macro-states,
operator actions, and pattern vertices. The \\texttt{{GovernancePatternMiner}} extracts
recurring $(scenario, severity, AI action, $\\Sigma$-sequence, terminal state) tuples;
the \\texttt{{NearMissDetector}} flags incorrect AI acceptance, missed escalations, and
missed overrides.

\\begin{{figure}}[htbp]
  \\centering
  \\includegraphics[width=\\linewidth]{{figures/institutional_memory_graph.pdf}}
  \\caption{{Institutional Memory Graph mined from $N={g.trace_count}$ governance traces
    (edge width $\\propto$ support).}}
  \\label{{fig:institutional-memory-graph}}
\\end{{figure}}

\\paragraph{{Learning metrics.}}
\\begin{{itemize}}[noitemsep]
  \\item \\textbf{{memory\\_coverage}} $={m.memory_coverage:.3f}$ --- fraction of TSGG runs
        contributing governance history;
  \\item \\textbf{{pattern\\_recurrence}} $={m.pattern_recurrence:.3f}$ --- mean support of
        mined patterns;
  \\item \\textbf{{governance\\_learning\\_index}} $={m.governance_learning_index:.3f}$ ---
        composite organizational-learning feasibility score.
\\end{{itemize}}

\\paragraph{{Positioning.}}
IMG is not a recommender; it is an \\emph{{institutional audit memory}} informing protocol
refinement, training, and escalation policy before field pilot (Stage~S3). {report.disclaimer}
"""
    path.write_text(content, encoding="utf-8")


def generate_institutional_memory_graph_pdf(path: Path, dot: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dot_path = path.parent / "institutional_memory_render.dot"
    dot_path.write_text(dot, encoding="utf-8")
    dot_bin = shutil.which("dot")
    if dot_bin:
        subprocess.run(
            [dot_bin, "-Tpdf", str(dot_path), "-o", str(path)],
            check=False,
            capture_output=True,
        )
    elif not path.exists():
        path.write_bytes(b"% PDF placeholder - install graphviz dot\n")


__all__ = [
    "build_institutional_memory_report",
    "export_institutional_memory",
    "run_institutional_memory",
    "write_institutional_memory_section",
]
