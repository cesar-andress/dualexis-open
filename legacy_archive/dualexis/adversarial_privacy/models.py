"""Adversarial privacy stress framework models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AdversarialAttackKind(StrEnum):
    """Privacy attacks beyond forbidden-key validation."""

    INDIRECT_IDENTITY_LEAKAGE = "indirect_identity_leakage"
    QUASI_IDENTIFIER_COMBINATIONS = "quasi_identifier_combinations"
    TEMPORAL_LINKAGE = "temporal_linkage_attack"
    REPEATED_EVENT_CORRELATION = "repeated_event_correlation"
    GRAPH_RECONSTRUCTION = "graph_reconstruction_attack"


class AdversarialPrivacyAttack(BaseModel):
    """One adversarial privacy stress probe."""

    model_config = ConfigDict(frozen=True)

    attack_id: str = Field(min_length=1, max_length=64)
    kind: AdversarialAttackKind
    description: str = Field(min_length=1, max_length=512)
    payloads: tuple[dict[str, object], ...] = Field(default_factory=tuple)


class AdversarialAttackResult(BaseModel):
    """Outcome of one adversarial attack."""

    model_config = ConfigDict(frozen=True)

    attack_id: str
    kind: AdversarialAttackKind
    description: str
    l1_blocked: bool
    attack_succeeded: bool
    reidentification_risk: float = Field(ge=0.0, le=1.0)
    semantic_leakage_score: float = Field(ge=0.0, le=1.0)
    violation_type: str = ""
    notes: str = ""


class AdversarialPrivacyMetrics(BaseModel):
    """Aggregate adversarial privacy metrics."""

    model_config = ConfigDict(frozen=True)

    reidentification_risk: float = Field(ge=0.0, le=1.0)
    privacy_attack_success_rate: float = Field(ge=0.0, le=1.0)
    semantic_leakage_score: float = Field(ge=0.0, le=1.0)
    privacy_resilience_index: float = Field(ge=0.0, le=1.0)
    fuzz_pass_rate: float = Field(ge=0.0, le=1.0)
    attack_count: int = Field(ge=0)
    l1_block_rate: float = Field(ge=0.0, le=1.0)


class AdversarialPrivacyReport(BaseModel):
    """Full stress report: legacy fuzz + adversarial attacks."""

    model_config = ConfigDict(frozen=True)

    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    disclaimer: str = Field(min_length=1)
    adversarial_results: tuple[AdversarialAttackResult, ...] = Field(default_factory=tuple)
    metrics: AdversarialPrivacyMetrics
    fuzz_case_count: int = Field(ge=0)
    fuzz_pass_count: int = Field(ge=0)


__all__ = [
    "AdversarialAttackKind",
    "AdversarialAttackResult",
    "AdversarialPrivacyAttack",
    "AdversarialPrivacyMetrics",
    "AdversarialPrivacyReport",
]
