"""Deterministic export mutations for violation-detection audit tasks."""

from __future__ import annotations

import copy
from typing import Any

from dualexis.evaluation.audit_tasks.gold_generator import MUTATION_FORBIDDEN_KEY
from dualexis.evaluation.exporters.models import ExportFormat


def _prov_relation_items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
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


def _prov_attr(entity: dict[str, Any], name: str) -> Any:
    for key in (name, f"ex:{name}", f"dualexis:{name}"):
        if key in entity:
            return entity[key]
    return None


def _set_prov_relations(payload: dict[str, Any], key: str, edges: list[dict[str, Any]]) -> None:
    if isinstance(payload.get(key), dict):
        payload[key] = {f"_:mut{i}": edge for i, edge in enumerate(edges)}
    else:
        payload[key] = edges


def apply_mutation(
    payload: dict[str, Any],
    export_format: ExportFormat,
    mutation: str,
) -> dict[str, Any]:
    """Return a deep-copied export with an injected audit violation."""
    mutated = copy.deepcopy(payload)
    if mutation == "remove_governance_disposition":
        _remove_governance(mutated, export_format)
    elif mutation == "inject_forbidden_privacy_key":
        _inject_forbidden_key(mutated, export_format, MUTATION_FORBIDDEN_KEY)
    elif mutation == "reorder_governance_steps":
        _reorder_governance(mutated, export_format)
    elif mutation == "remove_supporting_evidence_link":
        _remove_supporting_evidence(mutated, export_format)
    elif mutation == "remove_leakage_metadata":
        _remove_leakage_metadata(mutated, export_format)
    else:
        msg = f"Unknown mutation {mutation!r}"
        raise ValueError(msg)
    return mutated


def _remove_governance(payload: dict[str, Any], export_format: ExportFormat) -> None:
    if export_format == ExportFormat.TSGG:
        payload["governance_traces"] = []
    elif export_format == ExportFormat.FLAT_JSON:
        payload["records"] = [
            row for row in payload.get("records", []) if row.get("record_type") != "governance_step"
        ]
    elif export_format == ExportFormat.PROV:
        payload["entity"] = {
            key: value
            for key, value in payload.get("entity", {}).items()
            if value.get("prov:type") != "GovernanceStep"
        }
        payload["activity"] = {
            key: value
            for key, value in payload.get("activity", {}).items()
            if value.get("prov:type") != "GovernanceDecision"
        }
    elif export_format == ExportFormat.XES:
        for trace in payload.get("log", {}).get("traces", []):
            trace["events"] = [
                event
                for event in trace.get("events", [])
                if not str(event.get("concept:name", "")).startswith("Governance")
            ]


def _inject_forbidden_key(
    payload: dict[str, Any],
    export_format: ExportFormat,
    forbidden_key: str,
) -> None:
    if export_format == ExportFormat.TSGG:
        if payload.get("semantic_events"):
            payload["semantic_events"][0]["attributes"] = {forbidden_key: "injected"}
    elif export_format == ExportFormat.FLAT_JSON:
        for row in payload.get("records", []):
            if row.get("record_type") == "semantic_event":
                row.setdefault("attributes", {})[forbidden_key] = "injected"
                break
    elif export_format == ExportFormat.PROV:
        payload.setdefault("entity", {})["entity:injected-privacy"] = {
            "prov:type": "SemanticEvent",
            forbidden_key: "injected",
        }
    elif export_format == ExportFormat.XES:
        for trace in payload.get("log", {}).get("traces", []):
            trace.setdefault("events", []).append(
                {
                    "concept:name": "PrivacyViolationInjected",
                    "time:timestamp": "2026-01-01T12:00:00+00:00",
                    "lifecycle:transition": "complete",
                    f"dualexis:{forbidden_key}": "injected",
                }
            )


def _reorder_governance(payload: dict[str, Any], export_format: ExportFormat) -> None:
    if export_format == ExportFormat.TSGG:
        for trace in payload.get("governance_traces", []):
            steps = trace.get("steps", [])
            if len(steps) >= 2:
                steps[0]["step_index"], steps[1]["step_index"] = (
                    steps[1]["step_index"],
                    steps[0]["step_index"],
                )
    elif export_format == ExportFormat.FLAT_JSON:
        gov_rows = [
            row for row in payload.get("records", []) if row.get("record_type") == "governance_step"
        ]
        if len(gov_rows) >= 2:
            gov_rows[0]["attributes"]["step_index"], gov_rows[1]["attributes"]["step_index"] = (
                gov_rows[1]["attributes"]["step_index"],
                gov_rows[0]["attributes"]["step_index"],
            )
    elif export_format == ExportFormat.PROV:
        steps = [
            (key, value)
            for key, value in payload.get("entity", {}).items()
            if value.get("prov:type") == "GovernanceStep"
        ]
        if len(steps) >= 2:
            a_idx = _prov_attr(steps[0][1], "step_index")
            b_idx = _prov_attr(steps[1][1], "step_index")
            for entity in (steps[0][1], steps[1][1]):
                for key in ("step_index", "ex:step_index"):
                    if key in entity:
                        entity[key] = b_idx if entity is steps[0][1] else a_idx
    elif export_format == ExportFormat.XES:
        for trace in payload.get("log", {}).get("traces", []):
            gov_events = [
                event
                for event in trace.get("events", [])
                if str(event.get("concept:name", "")).startswith("Governance")
            ]
            if len(gov_events) >= 2:
                gov_events[0]["dualexis:step_index"], gov_events[1]["dualexis:step_index"] = (
                    gov_events[1]["dualexis:step_index"],
                    gov_events[0]["dualexis:step_index"],
                )


def _remove_supporting_evidence(payload: dict[str, Any], export_format: ExportFormat) -> None:
    if export_format == ExportFormat.TSGG:
        if payload.get("causal_transitions"):
            payload["causal_transitions"][0]["supporting_evidence_ids"] = []
        payload["links"] = [
            link
            for link in payload.get("links", [])
            if link.get("link_type") != "evidence_supports_transition"
        ]
    elif export_format == ExportFormat.FLAT_JSON:
        for row in payload.get("records", []):
            if row.get("record_type") == "causal_transition":
                row["attributes"]["supporting_evidence_ids"] = []
                row["related_ids"] = []
    elif export_format == ExportFormat.PROV:
        entities = payload.get("entity", {})
        kept = [
            edge
            for edge in _prov_relation_items(payload, "wasDerivedFrom")
            if "Evidence"
            not in str(entities.get(_prov_edge_value(edge, "prov:usedEntity", "usedEntity") or "", {}))
        ]
        _set_prov_relations(payload, "wasDerivedFrom", kept)
        _set_prov_relations(payload, "used", [])
    elif export_format == ExportFormat.XES:
        for trace in payload.get("log", {}).get("traces", []):
            for event in trace.get("events", []):
                if event.get("concept:name") == "CausalStateTransition":
                    event["dualexis:supporting_evidence_ids"] = []


def _remove_leakage_metadata(payload: dict[str, Any], export_format: ExportFormat) -> None:
    if export_format == ExportFormat.TSGG:
        payload.pop("benchmark_coupling", None)
    elif export_format == ExportFormat.FLAT_JSON:
        payload["records"] = [
            row
            for row in payload.get("records", [])
            if row.get("record_type") != "benchmark_coupling"
        ]
    elif export_format == ExportFormat.PROV:
        payload["entity"] = {
            key: value
            for key, value in payload.get("entity", {}).items()
            if value.get("prov:type") != "BenchmarkCouplingDisclosure"
        }
    elif export_format == ExportFormat.XES:
        for trace in payload.get("log", {}).get("traces", []):
            trace["events"] = [
                event
                for event in trace.get("events", [])
                if event.get("concept:name") != "BenchmarkCouplingDisclosed"
            ]


__all__ = ["apply_mutation"]
