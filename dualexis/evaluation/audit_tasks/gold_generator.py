"""Gold answer generation from TSGG run records."""

from __future__ import annotations

from dualexis.governance.formal_models import GovernanceMacroState
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.leakage_audit.scoring import BENCHMARK_DISCLOSURE
from dualexis.privacy_runtime.models import FORBIDDEN_BIOMETRIC_KEYS
from dualexis.tsgg.models import TsggRunRecord

from dualexis.evaluation.audit_tasks.models import AuditTaskId, AuditTaskKind, TaskGold


def generate_task_gold(
    record: TsggRunRecord,
    *,
    leakage_report: LeakageAuditReport | None = None,
) -> dict[AuditTaskId, TaskGold]:
    """Build deterministic gold answers for audit tasks A1--A7."""
    return {
        AuditTaskId.A1_EVIDENCE_TO_RECOMMENDATION: _gold_a1(record),
        AuditTaskId.A2_MISSING_HUMAN_DISPOSITION: _gold_a2(record),
        AuditTaskId.A3_PRIVACY_VIOLATION: _gold_a3(record),
        AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT: _gold_a4(record),
        AuditTaskId.A5_GOVERNANCE_APPEND_ONLY: _gold_a5(record),
        AuditTaskId.A6_BENCHMARK_COUPLING: _gold_a6(leakage_report),
        AuditTaskId.A7_EVACUATION_ZONE_COUNT: _gold_a7(record),
    }


def _gold_a1(record: TsggRunRecord) -> TaskGold:
    if not record.pipeline_output.recommendations:
        return TaskGold(
            task_id=AuditTaskId.A1_EVIDENCE_TO_RECOMMENDATION,
            kind=AuditTaskKind.QUERY,
            expected=None,
            applies=False,
        )
    recommendation = record.pipeline_output.recommendations[0]
    zone_transitions = [
        t
        for t in record.causal_trace.causal_transitions
        if t.zone_id == recommendation.target_zone_id
    ]
    if not zone_transitions:
        return TaskGold(
            task_id=AuditTaskId.A1_EVIDENCE_TO_RECOMMENDATION,
            kind=AuditTaskKind.QUERY,
            expected=None,
            applies=False,
        )
    transition = zone_transitions[-1]
    evidence_ids = tuple(ev.evidence_id for ev in transition.supporting_evidence)
    chain = {
        "evidence_ids": list(evidence_ids),
        "transition_id": str(transition.transition_id),
        "recommendation_id": str(recommendation.recommendation_id),
    }
    facts = frozenset(
        {
            f"evidence:{eid}" for eid in evidence_ids
        }
        | {f"transition:{transition.transition_id}", f"recommendation:{recommendation.recommendation_id}"}
    )
    return TaskGold(
        task_id=AuditTaskId.A1_EVIDENCE_TO_RECOMMENDATION,
        kind=AuditTaskKind.QUERY,
        expected=chain,
        gold_facts=facts,
        required_fields=frozenset({"evidence_ids", "transition_id", "recommendation_id"}),
    )


def _gold_a2(record: TsggRunRecord) -> TaskGold:
    missing: list[str] = []
    governed_cases = {trace.case_id for trace in record.governance_traces}
    for recommendation in record.pipeline_output.recommendations:
        if not recommendation.requires_human_review:
            continue
        case_id = f"{record.scenario_id}:{recommendation.target_zone_id}"
        if case_id not in governed_cases:
            missing.append(str(recommendation.recommendation_id))
            continue
        trace = next(t for t in record.governance_traces if t.case_id == case_id)
        if trace.terminal_macro_state == GovernanceMacroState.AI_RECOMMENDATION:
            missing.append(str(recommendation.recommendation_id))
    return TaskGold(
        task_id=AuditTaskId.A2_MISSING_HUMAN_DISPOSITION,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        expected=sorted(missing),
        gold_facts=frozenset(f"missing_disposition:{rid}" for rid in missing),
        required_fields=frozenset({"requires_human_review", "governance_trace"}),
    )


def _gold_a3(record: TsggRunRecord) -> TaskGold:
    violations: list[str] = []
    forbidden = next(iter(FORBIDDEN_BIOMETRIC_KEYS))
    for event in record.pipeline_output.normalized_events:
        for key, value in event.metadata.items():
            if key.lower() in FORBIDDEN_BIOMETRIC_KEYS or str(value).lower() in FORBIDDEN_BIOMETRIC_KEYS:
                violations.append(f"{event.event_id}:{key}")
    return TaskGold(
        task_id=AuditTaskId.A3_PRIVACY_VIOLATION,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        expected=sorted(violations),
        gold_facts=frozenset(violations) if violations else frozenset({f"probe:{forbidden}"}),
        required_fields=frozenset({"semantic_event", "attributes"}),
    )


def _gold_a4(record: TsggRunRecord) -> TaskGold:
    if not record.causal_trace.causal_transitions:
        return TaskGold(
            task_id=AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT,
            kind=AuditTaskKind.QUERY,
            expected=None,
            applies=False,
        )
    transition = record.causal_trace.causal_transitions[0]
    evidence_ids = [ev.evidence_id for ev in transition.supporting_evidence]
    expected = {
        "transition_id": str(transition.transition_id),
        "supporting_evidence_ids": evidence_ids,
    }
    return TaskGold(
        task_id=AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT,
        kind=AuditTaskKind.QUERY,
        expected=expected,
        gold_facts=frozenset(f"evidence:{eid}" for eid in evidence_ids)
        | {f"transition:{transition.transition_id}"},
        required_fields=frozenset({"transition_id", "supporting_evidence_ids"}),
    )


def _gold_a5(record: TsggRunRecord) -> TaskGold:
    ordered = True
    for trace in record.governance_traces:
        indices = [step.step_index for step in trace.steps]
        if indices != sorted(indices) or len(indices) != len(set(indices)):
            ordered = False
            break
    return TaskGold(
        task_id=AuditTaskId.A5_GOVERNANCE_APPEND_ONLY,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        expected=not ordered,
        gold_facts=frozenset({f"governance_ordered:{ordered}"}),
        required_fields=frozenset({"governance_step", "step_index"}),
    )


def _gold_a6(leakage_report: LeakageAuditReport | None) -> TaskGold:
    if leakage_report is None:
        return TaskGold(
            task_id=AuditTaskId.A6_BENCHMARK_COUPLING,
            kind=AuditTaskKind.QUERY,
            expected=None,
            applies=False,
        )
    expected = {
        "leakage_score": leakage_report.leakage_score,
        "procedural_independence": leakage_report.independence.procedural_independence,
        "benchmark_disclosure": leakage_report.benchmark_disclosure,
    }
    facts = frozenset(
        {
            f"leakage_score:{leakage_report.leakage_score}",
            f"pi_proc:{leakage_report.independence.procedural_independence}",
            f"disclosure:{leakage_report.benchmark_disclosure}",
        }
    )
    return TaskGold(
        task_id=AuditTaskId.A6_BENCHMARK_COUPLING,
        kind=AuditTaskKind.QUERY,
        expected=expected,
        gold_facts=facts,
        required_fields=frozenset(
            {"leakage_score", "procedural_independence", "benchmark_disclosure"}
        ),
    )


def _gold_a7(record: TsggRunRecord) -> TaskGold:
    if record.scenario_id != "evacuation_recommendation":
        return TaskGold(
            task_id=AuditTaskId.A7_EVACUATION_ZONE_COUNT,
            kind=AuditTaskKind.QUERY,
            expected=None,
            applies=False,
        )
    zones = {
        event.zone_id
        for event in record.pipeline_output.normalized_events
        if event.metadata.get("category") == "evacuation_stress_pattern"
    }
    return TaskGold(
        task_id=AuditTaskId.A7_EVACUATION_ZONE_COUNT,
        kind=AuditTaskKind.QUERY,
        expected=len(zones),
        gold_facts=frozenset(f"zone:{zone}" for zone in sorted(zones)),
        required_fields=frozenset({"semantic_event", "category", "zone_id"}),
    )


def gold_for_privacy_mutation(forbidden_key: str) -> TaskGold:
    """Gold when a forbidden privacy key is injected into a projection."""
    return TaskGold(
        task_id=AuditTaskId.A3_PRIVACY_VIOLATION,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        expected=[f"injected:{forbidden_key}"],
        gold_facts=frozenset({f"violation:{forbidden_key}"}),
        required_fields=frozenset({"semantic_event", "attributes"}),
    )


def gold_for_missing_disposition_mutation(recommendation_ids: list[str]) -> TaskGold:
    return TaskGold(
        task_id=AuditTaskId.A2_MISSING_HUMAN_DISPOSITION,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        expected=sorted(recommendation_ids),
        gold_facts=frozenset(f"missing_disposition:{rid}" for rid in recommendation_ids),
        required_fields=frozenset({"requires_human_review", "governance_trace"}),
    )


def gold_for_reordered_governance() -> TaskGold:
    return TaskGold(
        task_id=AuditTaskId.A5_GOVERNANCE_APPEND_ONLY,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        expected=True,
        gold_facts=frozenset({"governance_ordered:False"}),
        required_fields=frozenset({"governance_step", "step_index"}),
    )


def gold_for_removed_evidence_link(transition_id: str) -> TaskGold:
    return TaskGold(
        task_id=AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        expected={"transition_id": transition_id, "supporting_evidence_ids": []},
        gold_facts=frozenset({f"transition:{transition_id}", "evidence_removed"}),
        required_fields=frozenset({"transition_id", "supporting_evidence_ids"}),
    )


def gold_for_removed_leakage_metadata() -> TaskGold:
    return TaskGold(
        task_id=AuditTaskId.A6_BENCHMARK_COUPLING,
        kind=AuditTaskKind.QUERY,
        expected=None,
        gold_facts=frozenset({"leakage_removed"}),
        required_fields=frozenset(
            {"leakage_score", "procedural_independence", "benchmark_disclosure"}
        ),
    )


MUTATION_FORBIDDEN_KEY = next(iter(FORBIDDEN_BIOMETRIC_KEYS))
MUTATION_BENCHMARK_DISCLOSURE = BENCHMARK_DISCLOSURE


__all__ = [
    "MUTATION_BENCHMARK_DISCLOSURE",
    "MUTATION_FORBIDDEN_KEY",
    "generate_task_gold",
    "gold_for_missing_disposition_mutation",
    "gold_for_privacy_mutation",
    "gold_for_removed_evidence_link",
    "gold_for_removed_leakage_metadata",
    "gold_for_reordered_governance",
]
