"""Audit-comparison task and result models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditTaskId(StrEnum):
    """Registered post-hoc audit tasks (A1--A7)."""

    A1_EVIDENCE_TO_RECOMMENDATION = "A1_evidence_to_recommendation"
    A2_MISSING_HUMAN_DISPOSITION = "A2_missing_human_disposition"
    A3_PRIVACY_VIOLATION = "A3_privacy_violation"
    A4_CAUSAL_EVIDENCE_SUPPORT = "A4_causal_evidence_support"
    A5_GOVERNANCE_APPEND_ONLY = "A5_governance_append_only"
    A6_BENCHMARK_COUPLING = "A6_benchmark_coupling"
    A7_EVACUATION_ZONE_COUNT = "A7_evacuation_zone_count"


class AuditTaskKind(StrEnum):
    """Task evaluation mode."""

    QUERY = "query"
    VIOLATION_DETECTION = "violation_detection"


class TaskGold(BaseModel):
    """Machine-checkable gold answer for one task on one run."""

    model_config = ConfigDict(frozen=True)

    task_id: AuditTaskId
    kind: AuditTaskKind
    expected: Any
    gold_facts: frozenset[str] = Field(default_factory=frozenset)
    required_fields: frozenset[str] = Field(default_factory=frozenset)
    applies: bool = True


class TaskEvalResult(BaseModel):
    """Outcome of running one task against one export format."""

    model_config = ConfigDict(frozen=True)

    task_id: AuditTaskId
    export_format: str
    success: bool
    answer: Any = None
    extracted_facts: frozenset[str] = Field(default_factory=frozenset)
    query_hops: int = 0
    applicable: bool = True


class ViolationMetrics(BaseModel):
    """Precision/recall/F1 for violation-detection tasks."""

    model_config = ConfigDict(frozen=True)

    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)


__all__ = [
    "AuditTaskId",
    "AuditTaskKind",
    "TaskEvalResult",
    "TaskGold",
    "ViolationMetrics",
]
