"""XES / process-mining style trace export."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.tsgg.models import TsggRunRecord


def export_xes_log(
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> dict[str, Any]:
    """Export a simplified XES JSON log with one trace per governance case (or scenario)."""
    case_id = f"{record.scenario_id}-seed{record.seed}"
    events: list[dict[str, Any]] = []

    def append_event(
        *,
        activity: str,
        timestamp: datetime,
        lifecycle: str = "complete",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        events.append(
            {
                "concept:name": activity,
                "time:timestamp": timestamp.isoformat(),
                "lifecycle:transition": lifecycle,
                "dualexis:case_id": case_id,
                **(attributes or {}),
            }
        )

    for transition in record.causal_trace.causal_transitions:
        for evidence in transition.supporting_evidence:
            append_event(
                activity="EvidenceObserved",
                timestamp=evidence.timestamp,
                attributes={
                    "dualexis:evidence_id": evidence.evidence_id,
                    "dualexis:zone_id": evidence.zone_id,
                    "dualexis:kind": evidence.kind.value,
                },
            )
        append_event(
            activity="CausalStateTransition",
            timestamp=transition.timestamp,
            attributes={
                "dualexis:transition_id": str(transition.transition_id),
                "dualexis:zone_id": transition.zone_id,
                "dualexis:from_state": transition.from_state.value,
                "dualexis:to_state": transition.to_state.value,
                "dualexis:supporting_evidence_ids": [
                    ev.evidence_id for ev in transition.supporting_evidence
                ],
            },
        )

    for recommendation in record.pipeline_output.recommendations:
        append_event(
            activity="RecommendationIssued",
            timestamp=recommendation.created_at,
            attributes={
                "dualexis:recommendation_id": str(recommendation.recommendation_id),
                "dualexis:requires_human_review": recommendation.requires_human_review,
                "dualexis:human_review_status": recommendation.human_review_status.value,
                "dualexis:severity": recommendation.severity.value,
            },
        )

    for gov_trace in record.governance_traces:
        for step in gov_trace.steps:
            append_event(
                activity=f"Governance{step.symbol.value.title()}",
                timestamp=step.timestamp,
                attributes={
                    "dualexis:case_id": gov_trace.case_id,
                    "dualexis:step_index": step.step_index,
                    "dualexis:from_state": step.from_state.value,
                    "dualexis:to_state": step.to_state.value,
                },
            )

    for audit_entry in record.pipeline_output.audit_records:
        append_event(
            activity=f"Audit{audit_entry.action.value.title()}",
            timestamp=audit_entry.timestamp,
            attributes={
                "dualexis:audit_entry_id": audit_entry.entry_id,
                "dualexis:action": audit_entry.action.value,
            },
        )

    for event in record.pipeline_output.normalized_events:
        append_event(
            activity="SemanticEventObserved",
            timestamp=event.timestamp,
            attributes={
                "dualexis:event_id": str(event.event_id),
                "dualexis:zone_id": event.zone_id,
                "dualexis:category": event.metadata.get("category", ""),
            },
        )

    if leakage_report is not None:
        ts = (
            record.pipeline_output.audit_records[-1].timestamp
            if record.pipeline_output.audit_records
            else datetime(2026, 1, 1, 12, 0, 0)
        )
        append_event(
            activity="BenchmarkCouplingDisclosed",
            timestamp=ts,
            attributes={
                "dualexis:leakage_score": leakage_report.leakage_score,
                "dualexis:benchmark_disclosure": leakage_report.benchmark_disclosure,
                "dualexis:procedural_independence": (
                    leakage_report.independence.procedural_independence
                ),
            },
        )

    events.sort(key=lambda row: row["time:timestamp"])

    return {
        "format": "xes_json",
        "scenario_id": record.scenario_id,
        "seed": record.seed,
        "log": {
            "xes": "2.0",
            "global": {
                "concept:name": "DualexisSyntheticAuditTrace",
                "lifecycle:model": "standard",
            },
            "traces": [
                {
                    "concept:name": case_id,
                    "events": events,
                }
            ],
        },
    }


__all__ = ["export_xes_log"]
