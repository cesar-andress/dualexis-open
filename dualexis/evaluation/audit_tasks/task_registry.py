"""Registered audit-comparison tasks and mutation bindings."""

from __future__ import annotations

from dataclasses import dataclass

from dualexis.evaluation.audit_tasks.models import AuditTaskId, AuditTaskKind


@dataclass(frozen=True)
class AuditTaskSpec:
    task_id: AuditTaskId
    kind: AuditTaskKind
    description: str
    mutation: str | None = None


AUDIT_TASKS: tuple[AuditTaskSpec, ...] = (
    AuditTaskSpec(
        task_id=AuditTaskId.A1_EVIDENCE_TO_RECOMMENDATION,
        kind=AuditTaskKind.QUERY,
        description="Reconstruct evidence-to-recommendation chain.",
    ),
    AuditTaskSpec(
        task_id=AuditTaskId.A2_MISSING_HUMAN_DISPOSITION,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        description="Detect review-required recommendation without governance disposition.",
        mutation="remove_governance_disposition",
    ),
    AuditTaskSpec(
        task_id=AuditTaskId.A3_PRIVACY_VIOLATION,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        description="Detect forbidden privacy key in trace projection.",
        mutation="inject_forbidden_privacy_key",
    ),
    AuditTaskSpec(
        task_id=AuditTaskId.A4_CAUSAL_EVIDENCE_SUPPORT,
        kind=AuditTaskKind.QUERY,
        description="Identify supporting evidence for a causal transition.",
        mutation="remove_supporting_evidence_link",
    ),
    AuditTaskSpec(
        task_id=AuditTaskId.A5_GOVERNANCE_APPEND_ONLY,
        kind=AuditTaskKind.VIOLATION_DETECTION,
        description="Verify append-only governance step ordering.",
        mutation="reorder_governance_steps",
    ),
    AuditTaskSpec(
        task_id=AuditTaskId.A6_BENCHMARK_COUPLING,
        kind=AuditTaskKind.QUERY,
        description="Locate benchmark coupling disclosure fields.",
        mutation="remove_leakage_metadata",
    ),
    AuditTaskSpec(
        task_id=AuditTaskId.A7_EVACUATION_ZONE_COUNT,
        kind=AuditTaskKind.QUERY,
        description="Count affected zones in evacuation stress pattern.",
    ),
)


MUTATION_TASKS: tuple[AuditTaskSpec, ...] = tuple(
    task for task in AUDIT_TASKS if task.mutation is not None
)


__all__ = ["AUDIT_TASKS", "MUTATION_TASKS", "AuditTaskSpec"]
