"""Unified TSGG metrics."""

from __future__ import annotations

import statistics

from dualexis.cssg.metrics import compute_causal_graph_metrics
from dualexis.governance.formal_metrics import compute_formal_metrics
from dualexis.governance.formal_models import FormalGovernanceMetrics
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.scenario import ScenarioId
from dualexis.sssg.metrics import compute_state_graph_metrics
from dualexis.tsgg.models import TsggRunRecord, TsggUnifiedMetrics


def compute_tsgg_unified_metrics(
    records: list[TsggRunRecord],
    leakage_audit: LeakageAuditReport,
    *,
    formal_metrics: FormalGovernanceMetrics | None = None,
) -> TsggUnifiedMetrics:
    """Aggregate SSSG/CSSG, leakage, and governance into one metric vector."""
    if formal_metrics is None:
        all_gov_traces = []
        for record in records:
            all_gov_traces.extend(record.governance_traces)
        formal_metrics = compute_formal_metrics(all_gov_traces)

    governance_compliance = formal_metrics.governance_compliance_score
    decision_traceability = formal_metrics.decision_traceability

    if not records:
        trust = _tsgg_trust_index(
            transition_precision=0.0,
            transition_recall=0.0,
            causal_path_completeness=0.0,
            leakage_score=leakage_audit.leakage_score,
            procedural_independence=leakage_audit.independence.procedural_independence,
            distributional_independence=leakage_audit.independence.distributional_independence,
            governance_compliance=governance_compliance,
            decision_traceability=decision_traceability,
        )
        return TsggUnifiedMetrics(
            transition_precision=0.0,
            transition_recall=0.0,
            causal_path_completeness=0.0,
            leakage_score=round(leakage_audit.leakage_score, 4),
            procedural_independence=round(
                leakage_audit.independence.procedural_independence, 4
            ),
            distributional_independence=round(
                leakage_audit.independence.distributional_independence, 4
            ),
            governance_compliance_score=governance_compliance,
            decision_traceability=decision_traceability,
            tsgg_trust_index=trust,
        )

    tp_list: list[float] = []
    tr_list: list[float] = []
    causal_pc_list: list[float] = []

    for record in records:
        gt = load_scenario_ground_truth(ScenarioId(record.scenario_id))
        from dualexis.sssg.models import StateTransitionTrace

        sssg_view = StateTransitionTrace(
            scenario_id=record.causal_trace.scenario_id,
            seed=record.causal_trace.seed,
            zone_ids=record.causal_trace.zone_ids,
            transitions=record.causal_trace.transitions,
            snapshots=record.causal_trace.snapshots,
            edges=record.causal_trace.edges,
            final_states=record.causal_trace.final_states,
        )
        sssg_metrics = compute_state_graph_metrics(sssg_view, gt)
        causal_metrics = compute_causal_graph_metrics(record.causal_trace, gt)
        tp_list.append(sssg_metrics.transition_precision)
        tr_list.append(sssg_metrics.transition_recall)
        causal_pc_list.append(causal_metrics.causal_path_completeness)

    trust = _tsgg_trust_index(
        transition_precision=statistics.mean(tp_list),
        transition_recall=statistics.mean(tr_list),
        causal_path_completeness=statistics.mean(causal_pc_list),
        leakage_score=leakage_audit.leakage_score,
        procedural_independence=leakage_audit.independence.procedural_independence,
        distributional_independence=leakage_audit.independence.distributional_independence,
        governance_compliance=governance_compliance,
        decision_traceability=decision_traceability,
    )

    return TsggUnifiedMetrics(
        transition_precision=round(statistics.mean(tp_list), 4),
        transition_recall=round(statistics.mean(tr_list), 4),
        causal_path_completeness=round(statistics.mean(causal_pc_list), 4),
        leakage_score=round(leakage_audit.leakage_score, 4),
        procedural_independence=round(
            leakage_audit.independence.procedural_independence, 4
        ),
        distributional_independence=round(
            leakage_audit.independence.distributional_independence, 4
        ),
        governance_compliance_score=governance_compliance,
        decision_traceability=decision_traceability,
        tsgg_trust_index=trust,
    )


def _tsgg_trust_index(
    *,
    transition_precision: float,
    transition_recall: float,
    causal_path_completeness: float,
    leakage_score: float,
    procedural_independence: float,
    distributional_independence: float,
    governance_compliance: float,
    decision_traceability: float,
) -> float:
    state_quality = (transition_precision + transition_recall) / 2.0
    benchmark_trust = (
        0.5 * procedural_independence + 0.5 * distributional_independence
    ) * (1.0 - leakage_score)
    governance_trust = (governance_compliance + decision_traceability) / 2.0
    score = (
        0.30 * state_quality
        + 0.25 * causal_path_completeness
        + 0.25 * benchmark_trust
        + 0.20 * governance_trust
    )
    return round(max(0.0, min(1.0, score)), 4)


__all__ = ["compute_tsgg_unified_metrics"]
