"""Flat chronological JSON event log export (no typed graph schema)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.tsgg.models import TsggRunRecord


def _iso(ts: datetime) -> str:
    return ts.isoformat()


def export_flat_json_log(
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> dict[str, Any]:
    """Export a flat, time-ordered record list without graph edge typing."""
    records: list[dict[str, Any]] = []
    seq = 0

    def append(
        *,
        record_type: str,
        record_id: str,
        timestamp: datetime,
        attributes: dict[str, Any],
        related_ids: tuple[str, ...] = (),
    ) -> None:
        nonlocal seq
        seq += 1
        records.append(
            {
                "seq": seq,
                "record_type": record_type,
                "id": record_id,
                "timestamp": _iso(timestamp),
                "attributes": attributes,
                "related_ids": list(related_ids),
            }
        )

    for evidence in _iter_evidence(record):
        append(
            record_type="evidence",
            record_id=evidence["evidence_id"],
            timestamp=evidence["timestamp"],
            attributes={
                "kind": evidence["kind"],
                "zone_id": evidence["zone_id"],
                "tick": evidence["tick"],
                "metric_value": evidence.get("metric_value"),
            },
            related_ids=(),
        )

    for snapshot in record.causal_trace.snapshots:
        append(
            record_type="safety_state",
            record_id=str(snapshot.snapshot_id),
            timestamp=snapshot.timestamp,
            attributes={
                "zone_id": snapshot.zone_id,
                "state": snapshot.state.value,
                "tick": snapshot.tick,
            },
            related_ids=(),
        )

    for transition in record.causal_trace.causal_transitions:
        evidence_ids = tuple(ev.evidence_id for ev in transition.supporting_evidence)
        append(
            record_type="causal_transition",
            record_id=str(transition.transition_id),
            timestamp=transition.timestamp,
            attributes={
                "zone_id": transition.zone_id,
                "from_state": transition.from_state.value,
                "to_state": transition.to_state.value,
                "tick": transition.tick,
                "supporting_evidence_ids": list(evidence_ids),
            },
            related_ids=evidence_ids,
        )

    for recommendation in record.pipeline_output.recommendations:
        related = tuple(str(event_id) for event_id in recommendation.based_on_events)
        append(
            record_type="recommendation",
            record_id=str(recommendation.recommendation_id),
            timestamp=recommendation.created_at,
            attributes={
                "target_zone_id": recommendation.target_zone_id,
                "action": recommendation.action,
                "severity": recommendation.severity.value,
                "requires_human_review": recommendation.requires_human_review,
                "human_review_status": recommendation.human_review_status.value,
            },
            related_ids=related,
        )

    for gov_trace in record.governance_traces:
        prev_step_id: str | None = None
        for step in gov_trace.steps:
            step_id = f"{gov_trace.trace_id}:{step.step_index}"
            related = (prev_step_id,) if prev_step_id else ()
            append(
                record_type="governance_step",
                record_id=step_id,
                timestamp=step.timestamp,
                attributes={
                    "case_id": gov_trace.case_id,
                    "step_index": step.step_index,
                    "from_state": step.from_state.value,
                    "symbol": step.symbol.value,
                    "to_state": step.to_state.value,
                    "zone_id": gov_trace.zone_id,
                },
                related_ids=related,
            )
            prev_step_id = step_id

    for audit_entry in record.pipeline_output.audit_records:
        append(
            record_type="audit_entry",
            record_id=audit_entry.entry_id,
            timestamp=audit_entry.timestamp,
            attributes={
                "action": audit_entry.action.value,
                "node_id": audit_entry.node_id,
                "event_id": str(audit_entry.event_id) if audit_entry.event_id else None,
                "details": dict(audit_entry.details),
            },
            related_ids=(str(audit_entry.event_id),) if audit_entry.event_id else (),
        )

    for event in record.pipeline_output.normalized_events:
        append(
            record_type="semantic_event",
            record_id=str(event.event_id),
            timestamp=event.timestamp,
            attributes={
                "zone_id": event.zone_id,
                "category": event.metadata.get("category", ""),
                "event_type": event.event_type.value,
                "severity": event.severity.value,
            },
            related_ids=(),
        )

    if leakage_report is not None:
        append(
            record_type="benchmark_coupling",
            record_id=f"leakage:{record.scenario_id}:{record.seed}",
            timestamp=record.pipeline_output.audit_records[-1].timestamp
            if record.pipeline_output.audit_records
            else datetime(2026, 1, 1, 12, 0, 0),
            attributes={
                "leakage_score": leakage_report.leakage_score,
                "procedural_independence": leakage_report.independence.procedural_independence,
                "distributional_independence": (
                    leakage_report.independence.distributional_independence
                ),
                "benchmark_disclosure": leakage_report.benchmark_disclosure,
            },
            related_ids=(),
        )

    records.sort(key=lambda row: (row["timestamp"], row["seq"]))
    for index, row in enumerate(records, start=1):
        row["seq"] = index

    return {
        "format": "flat_json_event_log",
        "scenario_id": record.scenario_id,
        "seed": record.seed,
        "records": records,
    }


def _iter_evidence(record: TsggRunRecord) -> list[dict[str, Any]]:
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for transition in record.causal_trace.causal_transitions:
        for evidence in transition.supporting_evidence:
            if evidence.evidence_id in seen:
                continue
            seen.add(evidence.evidence_id)
            items.append(
                {
                    "evidence_id": evidence.evidence_id,
                    "kind": evidence.kind.value,
                    "zone_id": evidence.zone_id,
                    "tick": evidence.tick,
                    "timestamp": evidence.timestamp,
                    "metric_value": evidence.metric_value,
                }
            )
    return items


__all__ = ["export_flat_json_log"]
