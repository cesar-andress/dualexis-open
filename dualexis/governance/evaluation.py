"""Run governance simulation battery and export artefacts."""

from __future__ import annotations

import csv
import json
import random
from datetime import UTC, datetime
from pathlib import Path

from dualexis.governance.cases import DEFAULT_SCENARIOS, build_case_pool, sample_review_cases
from dualexis.governance.export import write_governance_evaluation_section, write_governance_metrics_tex
from dualexis.governance.graph import build_governance_graph_dot
from dualexis.governance.metrics import aggregate_metrics_by_profile
from dualexis.governance.models import (
    GovernanceEvaluationReport,
    OperatorDecision,
    OperatorProfile,
)
from dualexis.governance.simulator import CONTRIBUTION_TITLE, simulate_profile_decisions

DEFAULT_SIMULATION_ITERATIONS = 1000


def run_governance_evaluation(
    *,
    output_dir: Path,
    paper_tables: Path | None = None,
    paper_sections: Path | None = None,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    simulation_iterations: int = DEFAULT_SIMULATION_ITERATIONS,
    seed: int = 42,
    fast: bool = False,
) -> GovernanceEvaluationReport:
    """Simulate operator reviews and export governance metrics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    iterations = 50 if fast else simulation_iterations

    pool = build_case_pool(scenarios=scenarios, seeds=tuple(range(1, 6)) if fast else tuple(range(1, 21)))
    rng = random.Random(seed)
    cases = sample_review_cases(pool, count=iterations, rng=rng)

    all_decisions: list[OperatorDecision] = []
    for profile in OperatorProfile:
        profile_rng = random.Random(seed + hash(profile.value) % 10_000)
        all_decisions.extend(
            simulate_profile_decisions(cases, profile=profile, rng=profile_rng)
        )

    profile_metrics = aggregate_metrics_by_profile(all_decisions, cases)
    dot = build_governance_graph_dot()
    (output_dir / "governance_graph.dot").write_text(dot, encoding="utf-8")

    decisions_path = output_dir / "simulated_decisions.csv"
    _write_decisions_csv(decisions_path, all_decisions, cases)

    summary = {
        "contribution_title": CONTRIBUTION_TITLE,
        "simulation_iterations": iterations,
        "case_pool_size": len(pool),
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "profile_metrics": [m.model_dump() for m in profile_metrics],
    }
    (output_dir / "governance_evaluation.json").write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    metrics_rows = []
    for metrics in profile_metrics:
        metrics_rows.append(
            {
                "profile": metrics.profile.value,
                "acceptance_rate": metrics.acceptance_rate,
                "override_rate": metrics.override_rate,
                "escalation_rate": metrics.escalation_rate,
                "dismissal_rate": metrics.dismissal_rate,
                "mean_review_latency_seconds": metrics.mean_review_latency_seconds,
                "automation_bias_risk": metrics.bias_risks.automation_bias_risk,
                "under_reliance_risk": metrics.bias_risks.under_reliance_risk,
                "over_reliance_risk": metrics.bias_risks.over_reliance_risk,
            }
        )
    with (output_dir / "governance_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metrics_rows)

    report = GovernanceEvaluationReport(
        contribution_title=CONTRIBUTION_TITLE,
        simulation_iterations=iterations,
        case_pool_size=len(pool),
        profile_metrics=profile_metrics,
        dependency_graph_dot=dot,
        decisions_csv=str(decisions_path),
    )

    if paper_tables is not None:
        write_governance_metrics_tex(report, paper_tables / "governance_metrics.tex")
    if paper_sections is not None:
        write_governance_evaluation_section(report, paper_sections / "governance_evaluation.tex")

    return report


def _write_decisions_csv(
    path: Path,
    decisions: list[OperatorDecision],
    cases: list,
) -> None:
    by_case = {case.case_id: case for case in cases}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "profile",
                "action",
                "resulting_state",
                "latency_seconds",
                "ai_correct",
                "ai_confidence",
                "scenario_id",
            ],
        )
        writer.writeheader()
        for decision in decisions:
            case = by_case.get(decision.case_id)
            writer.writerow(
                {
                    "case_id": decision.case_id,
                    "profile": decision.profile.value,
                    "action": decision.action.value,
                    "resulting_state": decision.resulting_state.value,
                    "latency_seconds": decision.latency_seconds,
                    "ai_correct": case.ai_correct if case else "",
                    "ai_confidence": case.ai_confidence if case else "",
                    "scenario_id": case.scenario_id if case else "",
                }
            )


__all__ = ["DEFAULT_SIMULATION_ITERATIONS", "run_governance_evaluation"]
