"""Run formal governance audit."""

from __future__ import annotations

import csv
import json
import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

from dualexis.governance.cases import DEFAULT_SCENARIOS, build_case_pool, sample_review_cases
from dualexis.governance.formal_metrics import build_governance_graph, compute_formal_metrics
from dualexis.governance.formal_models import (
    FORMAL_FRAMEWORK_TITLE,
    GovernanceAuditReport,
)
from dualexis.governance.models import OperatorProfile
from dualexis.governance.simulator import simulate_profile_decisions
from dualexis.governance.state_machine import build_decision_trace

FORMAL_GOVERNANCE_DISCLAIMER = (
    "Formal governance state-machine audit on simulated operator dispositions. "
    "Mathematical model documents δ: S×Σ→S; metrics are synthetic feasibility descriptors."
)


def run_formal_governance_audit(
    *,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    simulation_iterations: int = 1000,
    seed: int = 42,
    profile: OperatorProfile = OperatorProfile.BALANCED,
    fast: bool = False,
) -> GovernanceAuditReport:
    """Build traces, governance graph, and formal metrics."""
    iterations = 50 if fast else simulation_iterations
    pool = build_case_pool(
        scenarios=scenarios,
        seeds=tuple(range(1, 6)) if fast else tuple(range(1, 21)),
    )
    rng = random.Random(seed)
    cases = sample_review_cases(pool, count=iterations, rng=rng)
    profile_rng = random.Random(seed + 17)
    decisions = simulate_profile_decisions(cases, profile=profile, rng=profile_rng)

    by_case = {case.case_id: case for case in cases}
    traces = []
    for decision in decisions:
        case = by_case.get(decision.case_id)
        if case is not None:
            traces.append(build_decision_trace(case, decision))

    metrics = compute_formal_metrics(traces)
    graph = build_governance_graph(traces)

    return GovernanceAuditReport(
        generated_at=datetime.now(tz=UTC),
        framework_title=FORMAL_FRAMEWORK_TITLE,
        graph=graph,
        metrics=metrics,
        traces=tuple(traces),
        trace_count=len(traces),
        simulation_iterations=iterations,
        disclaimer=FORMAL_GOVERNANCE_DISCLAIMER,
    )


def export_governance_audit_report(
    report: GovernanceAuditReport,
    output_dir: Path,
    *,
    paper_sections: Path | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "governance_audit_report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    (output_dir / "formal_governance_graph.dot").write_text(report.graph.dot, encoding="utf-8")

    metrics_path = output_dir / "formal_governance_metrics.csv"
    with metrics_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report.metrics.model_dump().keys()))
        writer.writeheader()
        writer.writerow(report.metrics.model_dump())

    matrix_path = output_dir / "transition_matrix.json"
    matrix_path.write_text(
        json.dumps(report.graph.transition_matrix, indent=2),
        encoding="utf-8",
    )

    traces_dir = output_dir / "traces"
    if traces_dir.exists():
        shutil.rmtree(traces_dir)
    traces_dir.mkdir(parents=True)
    for trace in report.traces[:100]:
        path = traces_dir / f"{trace.case_id}_{trace.trace_id.hex[:8]}.json"
        path.write_text(trace.model_dump_json(indent=2), encoding="utf-8")

    paths = {
        "report_json": str(report_path),
        "metrics_csv": str(metrics_path),
        "matrix_json": str(matrix_path),
        "graph_dot": str(output_dir / "formal_governance_graph.dot"),
    }

    if paper_sections is not None:
        from dualexis.governance.formal_export import write_formal_governance_model_section

        section = paper_sections / "formal_governance_model.tex"
        write_formal_governance_model_section(report, section)
        paths["section_tex"] = str(section)

    return paths


__all__ = [
    "FORMAL_GOVERNANCE_DISCLAIMER",
    "export_governance_audit_report",
    "run_formal_governance_audit",
]
