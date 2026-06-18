"""Native TSGG JSON export with typed stage linkage."""

from __future__ import annotations

from typing import Any

from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.tsgg.models import TsggRunRecord


def export_tsgg_native(
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> dict[str, Any]:
    """Export typed TSGG trace with explicit cross-stage links."""
    recommendations = []
    for recommendation in record.pipeline_output.recommendations:
        zone_transitions = [
            str(t.transition_id)
            for t in record.causal_trace.causal_transitions
            if t.zone_id == recommendation.target_zone_id
        ]
        recommendations.append(
            {
                "recommendation_id": str(recommendation.recommendation_id),
                "target_zone_id": recommendation.target_zone_id,
                "action": recommendation.action,
                "severity": recommendation.severity.value,
                "requires_human_review": recommendation.requires_human_review,
                "human_review_status": recommendation.human_review_status.value,
                "based_on_event_ids": [str(eid) for eid in recommendation.based_on_events],
                "derived_from_transition_ids": zone_transitions,
                "created_at": recommendation.created_at.isoformat(),
            }
        )

    causal_transitions = []
    for transition in record.causal_trace.causal_transitions:
        causal_transitions.append(
            {
                "transition_id": str(transition.transition_id),
                "zone_id": transition.zone_id,
                "tick": transition.tick,
                "from_state": transition.from_state.value,
                "to_state": transition.to_state.value,
                "supporting_evidence_ids": [
                    ev.evidence_id for ev in transition.supporting_evidence
                ],
                "timestamp": transition.timestamp.isoformat(),
            }
        )

    governance_traces = []
    for gov_trace in record.governance_traces:
        governance_traces.append(
            {
                "trace_id": str(gov_trace.trace_id),
                "case_id": gov_trace.case_id,
                "zone_id": gov_trace.zone_id,
                "terminal_macro_state": gov_trace.terminal_macro_state.value,
                "policy_compliant": gov_trace.policy_compliant,
                "steps": [
                    {
                        "step_index": step.step_index,
                        "from_state": step.from_state.value,
                        "symbol": step.symbol.value,
                        "to_state": step.to_state.value,
                        "timestamp": step.timestamp.isoformat(),
                    }
                    for step in gov_trace.steps
                ],
            }
        )

    semantic_events = [
        {
            "event_id": str(event.event_id),
            "zone_id": event.zone_id,
            "category": event.metadata.get("category", ""),
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
        }
        for event in record.pipeline_output.normalized_events
    ]

    payload: dict[str, Any] = {
        "format": "tsgg_native",
        "scenario_id": record.scenario_id,
        "seed": record.seed,
        "stage_counts": dict(record.stage_counts),
        "evidence": [
            {
                "evidence_id": ev.evidence_id,
                "kind": ev.kind.value,
                "zone_id": ev.zone_id,
                "tick": ev.tick,
                "timestamp": ev.timestamp.isoformat(),
            }
            for transition in record.causal_trace.causal_transitions
            for ev in transition.supporting_evidence
        ],
        "causal_transitions": causal_transitions,
        "recommendations": recommendations,
        "governance_traces": governance_traces,
        "audit_records": [
            {
                "entry_id": entry.entry_id,
                "action": entry.action.value,
                "timestamp": entry.timestamp.isoformat(),
                "event_id": str(entry.event_id) if entry.event_id else None,
            }
            for entry in record.pipeline_output.audit_records
        ],
        "semantic_events": semantic_events,
        "links": _build_links(record),
    }

    if leakage_report is not None:
        payload["benchmark_coupling"] = {
            "leakage_score": leakage_report.leakage_score,
            "procedural_independence": leakage_report.independence.procedural_independence,
            "distributional_independence": (
                leakage_report.independence.distributional_independence
            ),
            "benchmark_disclosure": leakage_report.benchmark_disclosure,
        }

    return payload


def _build_links(record: TsggRunRecord) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for transition in record.causal_trace.causal_transitions:
        tid = str(transition.transition_id)
        for evidence in transition.supporting_evidence:
            links.append(
                {
                    "link_type": "evidence_supports_transition",
                    "from_id": evidence.evidence_id,
                    "to_id": tid,
                }
            )
    for recommendation in record.pipeline_output.recommendations:
        rid = str(recommendation.recommendation_id)
        for transition in record.causal_trace.causal_transitions:
            if transition.zone_id != recommendation.target_zone_id:
                continue
            links.append(
                {
                    "link_type": "transition_informs_recommendation",
                    "from_id": str(transition.transition_id),
                    "to_id": rid,
                }
            )
    return links


__all__ = ["export_tsgg_native"]
