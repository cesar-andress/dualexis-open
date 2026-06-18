"""Standards-based PROV-JSON export via ProvPy (``prov`` package)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from prov.constants import PROV_TYPE
from prov.model import ProvDocument

from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.tsgg.models import TsggRunRecord

_NS = "ex"
_NS_URI = "https://dualexis.local/prov#"


def _entity_id(key: str) -> str:
    return f"{_NS}:{key}"


def _activity_id(key: str) -> str:
    return f"{_NS}:act-{key}"


def _agent_id(key: str) -> str:
    return f"{_NS}:agent-{key}"


def _build_prov_document(
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> ProvDocument:
    doc = ProvDocument()
    doc.add_namespace(_NS, _NS_URI)
    created_entities: set[str] = set()

    def _ensure_entity(key: str, attrs: dict[str, object]) -> None:
        if key in created_entities:
            return
        doc.entity(key).add_attributes(attrs)
        created_entities.add(key)

    doc.agent(_agent_id("system")).add_attributes(
        {PROV_TYPE: "SoftwareAgent", f"{_NS}:label": "dualexis-reference"}
    )
    doc.agent(_agent_id("operator")).add_attributes(
        {PROV_TYPE: "Person", f"{_NS}:label": "simulated-operator"}
    )

    for transition in record.causal_trace.causal_transitions:
        for evidence in transition.supporting_evidence:
            eid = _entity_id(evidence.evidence_id)
            _ensure_entity(
                eid,
                {
                    PROV_TYPE: "Evidence",
                    f"{_NS}:kind": evidence.kind.value,
                    f"{_NS}:zone_id": evidence.zone_id,
                    f"{_NS}:tick": evidence.tick,
                },
            )

        tid = _entity_id(str(transition.transition_id))
        _ensure_entity(
            tid,
            {
                PROV_TYPE: "CausalTransition",
                f"{_NS}:zone_id": transition.zone_id,
                f"{_NS}:from_state": transition.from_state.value,
                f"{_NS}:to_state": transition.to_state.value,
            },
        )
        act_id = _activity_id(f"infer-{transition.transition_id}")
        doc.activity(act_id).add_attributes(
            {
                PROV_TYPE: "StateInference",
                f"{_NS}:startTime": transition.timestamp.isoformat(),
                f"{_NS}:endTime": transition.timestamp.isoformat(),
            }
        )
        doc.wasGeneratedBy(tid, act_id)
        doc.wasAssociatedWith(act_id, _agent_id("system"))
        for evidence in transition.supporting_evidence:
            evid = _entity_id(evidence.evidence_id)
            doc.used(act_id, evid)
            doc.wasDerivedFrom(tid, evid)

    for recommendation in record.pipeline_output.recommendations:
        rid = _entity_id(str(recommendation.recommendation_id))
        _ensure_entity(
            rid,
            {
                PROV_TYPE: "Recommendation",
                f"{_NS}:action": recommendation.action,
                f"{_NS}:severity": recommendation.severity.value,
                f"{_NS}:requires_human_review": recommendation.requires_human_review,
                f"{_NS}:human_review_status": recommendation.human_review_status.value,
            },
        )
        act_id = _activity_id(f"recommend-{recommendation.recommendation_id}")
        doc.activity(act_id).add_attributes(
            {
                PROV_TYPE: "Reasoning",
                f"{_NS}:startTime": recommendation.created_at.isoformat(),
                f"{_NS}:endTime": recommendation.created_at.isoformat(),
            }
        )
        doc.wasGeneratedBy(rid, act_id)
        doc.wasAssociatedWith(act_id, _agent_id("system"))
        zone_transitions = [
            t
            for t in record.causal_trace.causal_transitions
            if t.zone_id == recommendation.target_zone_id
        ]
        if zone_transitions:
            doc.wasDerivedFrom(rid, _entity_id(str(zone_transitions[-1].transition_id)))
        for event_id in recommendation.based_on_events:
            doc.wasDerivedFrom(rid, _entity_id(f"event-{event_id}"))

    for event in record.pipeline_output.normalized_events:
        eid = _entity_id(f"sem-{event.event_id}")
        _ensure_entity(
            eid,
            {
                PROV_TYPE: "SemanticEvent",
                f"{_NS}:event_id": str(event.event_id),
                f"{_NS}:zone_id": event.zone_id,
                f"{_NS}:category": event.metadata.get("category", ""),
            },
        )

    for gov_trace in record.governance_traces:
        for step in gov_trace.steps:
            sid = _entity_id(f"{gov_trace.trace_id}-{step.step_index}")
            _ensure_entity(
                sid,
                {
                    PROV_TYPE: "GovernanceStep",
                    f"{_NS}:case_id": gov_trace.case_id,
                    f"{_NS}:step_index": step.step_index,
                    f"{_NS}:from_state": step.from_state.value,
                    f"{_NS}:symbol": step.symbol.value,
                    f"{_NS}:to_state": step.to_state.value,
                },
            )
            act_id = _activity_id(f"gov-{gov_trace.trace_id}-{step.step_index}")
            doc.activity(act_id).add_attributes(
                {
                    PROV_TYPE: "GovernanceDecision",
                    f"{_NS}:startTime": step.timestamp.isoformat(),
                    f"{_NS}:endTime": step.timestamp.isoformat(),
                }
            )
            doc.wasGeneratedBy(sid, act_id)
            doc.wasAssociatedWith(act_id, _agent_id("operator"))
            if step.step_index > 0:
                prev = _entity_id(f"{gov_trace.trace_id}-{step.step_index - 1}")
                doc.wasDerivedFrom(sid, prev)

    if leakage_report is not None:
        _ensure_entity(
            _entity_id("benchmark-coupling"),
            {
                PROV_TYPE: "BenchmarkCouplingDisclosure",
                f"{_NS}:leakage_score": leakage_report.leakage_score,
                f"{_NS}:procedural_independence": (
                    leakage_report.independence.procedural_independence
                ),
                f"{_NS}:distributional_independence": (
                    leakage_report.independence.distributional_independence
                ),
                f"{_NS}:benchmark_disclosure": leakage_report.benchmark_disclosure,
            },
        )

    return doc


def prov_document_to_dict(doc: ProvDocument) -> dict[str, Any]:
    """Serialize a ProvDocument to a PROV-JSON dict (round-trip safe)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        path = Path(handle.name)
    try:
        doc.serialize(str(path), format="json")
        payload = json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)
    return payload


def export_prov_document(
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> dict[str, Any]:
    """Export standards-based PROV-JSON from a TSGG run record."""
    doc = _build_prov_document(record, leakage_report=leakage_report)
    payload = prov_document_to_dict(doc)
    payload["format"] = "prov_json"
    payload["scenario_id"] = record.scenario_id
    payload["seed"] = record.seed
    return payload


def roundtrip_prov_document(payload: dict[str, Any]) -> ProvDocument:
    """Deserialize PROV-JSON dict through ProvPy (for validation tests)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        path = Path(handle.name)
        serializable = {
            key: value
            for key, value in payload.items()
            if key not in {"format", "scenario_id", "seed"}
        }
        path.write_text(json.dumps(serializable), encoding="utf-8")
    try:
        return ProvDocument.deserialize(str(path))
    finally:
        path.unlink(missing_ok=True)


__all__ = [
    "_build_prov_document",
    "export_prov_document",
    "prov_document_to_dict",
    "roundtrip_prov_document",
]
