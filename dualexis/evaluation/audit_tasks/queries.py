"""Deterministic audit-task evaluators per export format."""

from __future__ import annotations

from typing import Any

from dualexis.evaluation.audit_tasks.models import AuditTaskId, TaskEvalResult, TaskGold
from dualexis.evaluation.exporters.models import ExportFormat
from dualexis.privacy_runtime.models import FORBIDDEN_BIOMETRIC_KEYS


def evaluate_task(
    task_id: AuditTaskId,
    export_format: ExportFormat,
    payload: dict[str, Any],
    gold: TaskGold,
) -> TaskEvalResult:
    if not gold.applies:
        return TaskEvalResult(
            task_id=task_id,
            export_format=export_format.value,
            success=True,
            applicable=False,
        )
    evaluator = _EVALUATORS[task_id][export_format]
    answer, facts, hops = evaluator(payload)
    success = _answers_match(task_id, answer, gold.expected)
    return TaskEvalResult(
        task_id=task_id,
        export_format=export_format.value,
        success=success,
        answer=answer,
        extracted_facts=facts,
        query_hops=hops,
    )


def _answers_match(task_id: AuditTaskId, answer: Any, expected: Any) -> bool:
    if task_id == AuditTaskId.A1_EVIDENCE_TO_RECOMMENDATION:
        if not isinstance(answer, dict) or not isinstance(expected, dict):
            return False
        return (
            set(answer.get("evidence_ids", [])) == set(expected.get("evidence_ids", []))
            and answer.get("transition_id") == expected.get("transition_id")
            and answer.get("recommendation_id") == expected.get("recommendation_id")
        )
    if task_id in {
        AuditTaskId.A2_MISSING_HUMAN_DISPOSITION,
        AuditTaskId.A3_PRIVACY_VIOLATION,
    }:
        if task_id == AuditTaskId.A3_PRIVACY_VIOLATION and expected:
            if str(expected[0]).startswith("injected:"):
                key = str(expected[0]).split(":", 1)[1]
                return any(key in str(item) for item in (answer or []))
        return sorted(answer or []) == sorted(expected or [])
    if task_id == AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT:
        if not isinstance(answer, dict) or not isinstance(expected, dict):
            return False
        return (
            answer.get("transition_id") == expected.get("transition_id")
            and sorted(answer.get("supporting_evidence_ids", []))
            == sorted(expected.get("supporting_evidence_ids", []))
        )
    if task_id == AuditTaskId.A5_GOVERNANCE_APPEND_ONLY:
        return bool(answer) == bool(expected)
    if task_id == AuditTaskId.A6_BENCHMARK_COUPLING:
        if expected is None:
            return answer is None
        if not isinstance(answer, dict) or not isinstance(expected, dict):
            return False
        return (
            answer.get("leakage_score") == expected.get("leakage_score")
            and answer.get("procedural_independence") == expected.get("procedural_independence")
            and answer.get("benchmark_disclosure") == expected.get("benchmark_disclosure")
        )
    if task_id == AuditTaskId.A7_EVACUATION_ZONE_COUNT:
        return answer == expected
    return answer == expected


def _tsgg_a1(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    recommendations = payload.get("recommendations", [])
    if not recommendations:
        return None, frozenset(), 0
    rec = recommendations[0]
    transition_id = (rec.get("derived_from_transition_ids") or [None])[-1]
    evidence_ids: list[str] = []
    hops = 1
    for transition in payload.get("causal_transitions", []):
        if transition.get("transition_id") == transition_id:
            evidence_ids = list(transition.get("supporting_evidence_ids", []))
            hops = 2
            break
    answer = {
        "evidence_ids": evidence_ids,
        "transition_id": transition_id,
        "recommendation_id": rec.get("recommendation_id"),
    }
    facts = frozenset(
        {f"evidence:{eid}" for eid in evidence_ids}
        | {f"transition:{transition_id}", f"recommendation:{rec.get('recommendation_id')}"}
    )
    return answer, facts, hops


def _tsgg_a2(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    missing = []
    for rec in payload.get("recommendations", []):
        if not rec.get("requires_human_review"):
            continue
        rid = rec.get("recommendation_id")
        zone = rec.get("target_zone_id")
        trace = next(
            (t for t in payload.get("governance_traces", []) if t.get("zone_id") == zone),
            None,
        )
        if trace is None or trace.get("terminal_macro_state") == "ai_recommendation":
            missing.append(rid)
    return missing, frozenset(f"missing_disposition:{m}" for m in missing), 2


def _tsgg_a3(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    violations = []
    for event in payload.get("semantic_events", []):
        attrs = event.get("attributes", {})
        for key, value in {**event, **attrs}.items():
            if str(key).lower() in FORBIDDEN_BIOMETRIC_KEYS:
                violations.append(
                    f"injected:{key}" if value == "injected" else f"{event.get('event_id')}:{key}"
                )
    return violations, frozenset(violations), 1


def _tsgg_a4(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    transitions = payload.get("causal_transitions", [])
    if not transitions:
        return None, frozenset(), 0
    transition = transitions[0]
    answer = {
        "transition_id": transition.get("transition_id"),
        "supporting_evidence_ids": list(transition.get("supporting_evidence_ids", [])),
    }
    facts = frozenset(
        {f"evidence:{eid}" for eid in answer["supporting_evidence_ids"]}
        | {f"transition:{transition.get('transition_id')}"}
    )
    return answer, facts, 1


def _tsgg_a5(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    violation = False
    for trace in payload.get("governance_traces", []):
        indices = [step.get("step_index") for step in trace.get("steps", [])]
        if indices != sorted(indices):
            violation = True
    return violation, frozenset({f"governance_ordered:{not violation}"}), 1


def _tsgg_a6(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    coupling = payload.get("benchmark_coupling")
    if not coupling:
        return None, frozenset(), 0
    answer = {
        "leakage_score": coupling.get("leakage_score"),
        "procedural_independence": coupling.get("procedural_independence"),
        "benchmark_disclosure": coupling.get("benchmark_disclosure"),
    }
    facts = frozenset(
        {
            f"leakage_score:{answer['leakage_score']}",
            f"pi_proc:{answer['procedural_independence']}",
            f"disclosure:{answer['benchmark_disclosure']}",
        }
    )
    return answer, facts, 1


def _tsgg_a7(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    zones = {
        event.get("zone_id")
        for event in payload.get("semantic_events", [])
        if event.get("category") == "evacuation_stress_pattern"
    }
    return len(zones), frozenset(f"zone:{z}" for z in zones if z), 1


def _flat_a1(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    records = payload.get("records", [])
    rec = next((r for r in records if r.get("record_type") == "recommendation"), None)
    if rec is None:
        return None, frozenset(), 0
    hops = 1
    transition_id = None
    evidence_ids: list[str] = []
    zone = rec.get("attributes", {}).get("target_zone_id")
    transition = next(
        (
            r
            for r in records
            if r.get("record_type") == "causal_transition"
            and r.get("attributes", {}).get("zone_id") == zone
        ),
        None,
    )
    if transition:
        transition_id = transition.get("id")
        evidence_ids = list(transition.get("attributes", {}).get("supporting_evidence_ids", []))
        hops = 2
    answer = {
        "evidence_ids": evidence_ids,
        "transition_id": transition_id,
        "recommendation_id": rec.get("id"),
    }
    facts = frozenset(
        {f"evidence:{eid}" for eid in evidence_ids}
        | ({f"transition:{transition_id}"} if transition_id else set())
        | {f"recommendation:{rec.get('id')}"}
    )
    return answer, facts, hops


def _flat_a2(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    gov_zones = {
        row.get("attributes", {}).get("zone_id")
        for row in payload.get("records", [])
        if row.get("record_type") == "governance_step"
    }
    missing = []
    for row in payload.get("records", []):
        if row.get("record_type") != "recommendation":
            continue
        attrs = row.get("attributes", {})
        if not attrs.get("requires_human_review"):
            continue
        if attrs.get("target_zone_id") not in gov_zones:
            missing.append(row.get("id"))
    return missing, frozenset(f"missing_disposition:{m}" for m in missing), 2


def _flat_a3(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    violations = []
    for row in payload.get("records", []):
        if row.get("record_type") != "semantic_event":
            continue
        for key in row.get("attributes", {}):
            if key.lower() in FORBIDDEN_BIOMETRIC_KEYS:
                violations.append(
                    f"injected:{key}"
                    if row["attributes"][key] == "injected"
                    else f"{row.get('id')}:{key}"
                )
    return violations, frozenset(violations), 1


def _flat_a4(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    transition = next(
        (r for r in payload.get("records", []) if r.get("record_type") == "causal_transition"),
        None,
    )
    if transition is None:
        return None, frozenset(), 0
    evidence_ids = list(transition.get("attributes", {}).get("supporting_evidence_ids", []))
    answer = {"transition_id": transition.get("id"), "supporting_evidence_ids": evidence_ids}
    return answer, frozenset({f"transition:{transition.get('id')}"} | {f"evidence:{e}" for e in evidence_ids}), 1


def _flat_a5(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    by_case: dict[str, list[int]] = {}
    for row in payload.get("records", []):
        if row.get("record_type") != "governance_step":
            continue
        case = row.get("attributes", {}).get("case_id", "default")
        by_case.setdefault(case, []).append(row.get("attributes", {}).get("step_index", 0))
    violation = any(indices != sorted(indices) for indices in by_case.values())
    return violation, frozenset({f"governance_ordered:{not violation}"}), 1


def _flat_a6(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    row = next(
        (r for r in payload.get("records", []) if r.get("record_type") == "benchmark_coupling"),
        None,
    )
    if row is None:
        return None, frozenset(), 0
    attrs = row.get("attributes", {})
    answer = {
        "leakage_score": attrs.get("leakage_score"),
        "procedural_independence": attrs.get("procedural_independence"),
        "benchmark_disclosure": attrs.get("benchmark_disclosure"),
    }
    return answer, frozenset({f"leakage_score:{answer['leakage_score']}"}), 1


def _flat_a7(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    zones = {
        row.get("attributes", {}).get("zone_id")
        for row in payload.get("records", [])
        if row.get("record_type") == "semantic_event"
        and row.get("attributes", {}).get("category") == "evacuation_stress_pattern"
    }
    zones.discard(None)
    return len(zones), frozenset(f"zone:{z}" for z in zones), 1


def _prov_relations(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = payload.get(key, {})
    if isinstance(raw, dict):
        return list(raw.values())
    if isinstance(raw, list):
        return raw
    return []


def _prov_edge_value(edge: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = edge.get(key)
        if value:
            return str(value)
    return None


def _prov_find_derived(prov: dict[str, Any], entity_id: str) -> list[str]:
    return [
        used
        for edge in _prov_relations(prov, "wasDerivedFrom")
        if (used := _prov_edge_value(edge, "prov:usedEntity", "usedEntity"))
        and _prov_edge_value(edge, "prov:generatedEntity", "generatedEntity") == entity_id
    ]


def _prov_scalar(value: Any) -> Any:
    if isinstance(value, dict) and "$" in value:
        return value["$"]
    return value


def _prov_attr(entity: dict[str, Any], name: str) -> Any:
    for key in (name, f"ex:{name}", f"dualexis:{name}"):
        if key in entity:
            return _prov_scalar(entity[key])
    return None


def _prov_local_id(qualified: str) -> str:
    if ":" in qualified:
        return qualified.split(":", 1)[1]
    return qualified


def _prov_a1(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    entities = payload.get("entity", {})
    rec_id = next((k for k, v in entities.items() if v.get("prov:type") == "Recommendation"), None)
    if rec_id is None:
        return None, frozenset(), 0
    hops = 1
    parents = _prov_find_derived(payload, rec_id)
    transition_id = next(
        (p for p in parents if entities.get(p, {}).get("prov:type") == "CausalTransition"),
        None,
    )
    evidence_ids = []
    if transition_id:
        hops = 2
        evidence_ids = [
            _prov_local_id(p)
            for p in _prov_find_derived(payload, transition_id)
            if entities.get(p, {}).get("prov:type") == "Evidence"
        ]
        if evidence_ids:
            hops = 3
    answer = {
        "evidence_ids": evidence_ids,
        "transition_id": _prov_local_id(transition_id) if transition_id else None,
        "recommendation_id": _prov_local_id(rec_id),
    }
    return answer, frozenset({f"recommendation:{answer['recommendation_id']}"}), hops


def _prov_a2(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    entities = payload.get("entity", {})
    gov_cases = {
        _prov_attr(value, "case_id")
        for value in entities.values()
        if value.get("prov:type") == "GovernanceStep"
    }
    missing = []
    for key, value in entities.items():
        if value.get("prov:type") != "Recommendation":
            continue
        if not _prov_attr(value, "requires_human_review"):
            continue
        if not gov_cases:
            missing.append(_prov_local_id(key))
    return missing, frozenset(f"missing_disposition:{m}" for m in missing), 2


def _prov_a3(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    violations = []
    for key, value in payload.get("entity", {}).items():
        for field in value:
            bare = field.split(":", 1)[-1]
            if bare.lower() in FORBIDDEN_BIOMETRIC_KEYS:
                violations.append(
                    f"injected:{bare}" if value[field] == "injected" else f"{key}:{bare}"
                )
    return violations, frozenset(violations), 1


def _prov_a4(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    entities = payload.get("entity", {})
    transition_id = next(
        (key for key, value in entities.items() if value.get("prov:type") == "CausalTransition"),
        None,
    )
    if transition_id is None:
        return None, frozenset(), 0
    evidence_ids = [_prov_local_id(p) for p in _prov_find_derived(payload, transition_id)]
    answer = {
        "transition_id": _prov_local_id(transition_id),
        "supporting_evidence_ids": evidence_ids,
    }
    return answer, frozenset({f"transition:{answer['transition_id']}"}), 2


def _prov_a5(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    by_case: dict[str, list[int]] = {}
    for value in payload.get("entity", {}).values():
        if value.get("prov:type") != "GovernanceStep":
            continue
        case = _prov_attr(value, "case_id") or "default"
        by_case.setdefault(str(case), []).append(int(_prov_attr(value, "step_index") or 0))
    violation = any(indices != sorted(indices) for indices in by_case.values())
    return violation, frozenset({f"governance_ordered:{not violation}"}), 1


def _prov_a6(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    entity = next(
        (
            value
            for value in payload.get("entity", {}).values()
            if value.get("prov:type") == "BenchmarkCouplingDisclosure"
        ),
        None,
    )
    if entity is None:
        return None, frozenset(), 0
    answer = {
        "leakage_score": _prov_attr(entity, "leakage_score"),
        "procedural_independence": _prov_attr(entity, "procedural_independence"),
        "benchmark_disclosure": _prov_attr(entity, "benchmark_disclosure"),
    }
    return answer, frozenset({f"leakage_score:{answer['leakage_score']}"}), 1


def _prov_a7(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    zones = {
        _prov_attr(value, "zone_id")
        for value in payload.get("entity", {}).values()
        if value.get("prov:type") == "SemanticEvent"
        and _prov_attr(value, "category") == "evacuation_stress_pattern"
    }
    zones.discard(None)
    return len(zones), frozenset(f"zone:{z}" for z in zones if z), 1


def _xes_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    traces = payload.get("log", {}).get("traces", [])
    if not traces:
        return []
    return list(traces[0].get("events", []))


def _xes_a1(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    events = _xes_events(payload)
    rec = next((e for e in events if e.get("concept:name") == "RecommendationIssued"), None)
    if rec is None:
        return None, frozenset(), 0
    rec_id = rec.get("dualexis:recommendation_id")
    transition = next((e for e in events if e.get("concept:name") == "CausalStateTransition"), None)
    evidence_ids = list(transition.get("dualexis:supporting_evidence_ids", [])) if transition else []
    answer = {
        "evidence_ids": evidence_ids,
        "transition_id": transition.get("dualexis:transition_id") if transition else None,
        "recommendation_id": rec_id,
    }
    hops = 3 if evidence_ids else 2 if transition else 1
    return answer, frozenset({f"recommendation:{rec_id}"}), hops


def _xes_a2(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    events = _xes_events(payload)
    gov_cases = {
        e.get("dualexis:case_id")
        for e in events
        if str(e.get("concept:name", "")).startswith("Governance")
    }
    missing = []
    for event in events:
        if event.get("concept:name") != "RecommendationIssued":
            continue
        if not event.get("dualexis:requires_human_review"):
            continue
        if not gov_cases:
            missing.append(event.get("dualexis:recommendation_id"))
    return missing, frozenset(f"missing_disposition:{m}" for m in missing), 2


def _xes_a3(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    violations = []
    for event in _xes_events(payload):
        for key in event:
            if key.replace("dualexis:", "").lower() in FORBIDDEN_BIOMETRIC_KEYS:
                violations.append(f"injected:{key.replace('dualexis:', '')}")
    return violations, frozenset(violations), 1


def _xes_a4(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    transition = next(
        (e for e in _xes_events(payload) if e.get("concept:name") == "CausalStateTransition"),
        None,
    )
    if transition is None:
        return None, frozenset(), 0
    evidence_ids = list(transition.get("dualexis:supporting_evidence_ids", []))
    answer = {
        "transition_id": transition.get("dualexis:transition_id"),
        "supporting_evidence_ids": evidence_ids,
    }
    return answer, frozenset({f"transition:{answer['transition_id']}"}), 1


def _xes_a5(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    by_case: dict[str, list[int]] = {}
    for event in _xes_events(payload):
        if not str(event.get("concept:name", "")).startswith("Governance"):
            continue
        case = event.get("dualexis:case_id", "default")
        by_case.setdefault(case, []).append(event.get("dualexis:step_index", 0))
    violation = any(indices != sorted(indices) for indices in by_case.values())
    return violation, frozenset({f"governance_ordered:{not violation}"}), 1


def _xes_a6(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    event = next(
        (e for e in _xes_events(payload) if e.get("concept:name") == "BenchmarkCouplingDisclosed"),
        None,
    )
    if event is None:
        return None, frozenset(), 0
    answer = {
        "leakage_score": event.get("dualexis:leakage_score"),
        "procedural_independence": event.get("dualexis:procedural_independence"),
        "benchmark_disclosure": event.get("dualexis:benchmark_disclosure"),
    }
    return answer, frozenset({f"leakage_score:{answer['leakage_score']}"}), 1


def _xes_a7(payload: dict[str, Any]) -> tuple[Any, frozenset[str], int]:
    zones = {
        event.get("dualexis:zone_id")
        for event in _xes_events(payload)
        if event.get("concept:name") == "SemanticEventObserved"
        and event.get("dualexis:category") == "evacuation_stress_pattern"
    }
    zones.discard(None)
    return len(zones), frozenset(f"zone:{z}" for z in zones), 1


_EVALUATORS = {
    AuditTaskId.A1_EVIDENCE_TO_RECOMMENDATION: {
        ExportFormat.TSGG: _tsgg_a1,
        ExportFormat.FLAT_JSON: _flat_a1,
        ExportFormat.PROV: _prov_a1,
        ExportFormat.XES: _xes_a1,
    },
    AuditTaskId.A2_MISSING_HUMAN_DISPOSITION: {
        ExportFormat.TSGG: _tsgg_a2,
        ExportFormat.FLAT_JSON: _flat_a2,
        ExportFormat.PROV: _prov_a2,
        ExportFormat.XES: _xes_a2,
    },
    AuditTaskId.A3_PRIVACY_VIOLATION: {
        ExportFormat.TSGG: _tsgg_a3,
        ExportFormat.FLAT_JSON: _flat_a3,
        ExportFormat.PROV: _prov_a3,
        ExportFormat.XES: _xes_a3,
    },
    AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT: {
        ExportFormat.TSGG: _tsgg_a4,
        ExportFormat.FLAT_JSON: _flat_a4,
        ExportFormat.PROV: _prov_a4,
        ExportFormat.XES: _xes_a4,
    },
    AuditTaskId.A5_GOVERNANCE_APPEND_ONLY: {
        ExportFormat.TSGG: _tsgg_a5,
        ExportFormat.FLAT_JSON: _flat_a5,
        ExportFormat.PROV: _prov_a5,
        ExportFormat.XES: _xes_a5,
    },
    AuditTaskId.A6_BENCHMARK_COUPLING: {
        ExportFormat.TSGG: _tsgg_a6,
        ExportFormat.FLAT_JSON: _flat_a6,
        ExportFormat.PROV: _prov_a6,
        ExportFormat.XES: _xes_a6,
    },
    AuditTaskId.A7_EVACUATION_ZONE_COUNT: {
        ExportFormat.TSGG: _tsgg_a7,
        ExportFormat.FLAT_JSON: _flat_a7,
        ExportFormat.PROV: _prov_a7,
        ExportFormat.XES: _xes_a7,
    },
}


__all__ = ["evaluate_task"]
