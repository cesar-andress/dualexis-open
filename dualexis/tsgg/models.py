"""Trusted Safety State Governance Graph (TSGG) unified models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dualexis.cssg.models import CausalStateTransitionTrace
from dualexis.governance.formal_models import GovernanceDecisionTrace
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.pipeline.models import PipelineOutput
from dualexis.sssg.models import StateTransitionTrace


class TsggPipelineStage(StrEnum):
    """Ordered stages of the TSGG pipeline."""

    EVIDENCE = "evidence"
    SAFETY_STATE = "safety_state"
    CAUSAL_TRANSITION = "causal_transition"
    RECOMMENDATION = "recommendation"
    GOVERNANCE_DECISION = "governance_decision"
    AUDIT_TRACE = "audit_trace"


class TsggRunRecord(BaseModel):
    """One end-to-end TSGG execution for (scenario, seed)."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    seed: int
    causal_trace: CausalStateTransitionTrace
    pipeline_output: PipelineOutput
    governance_traces: tuple[GovernanceDecisionTrace, ...] = Field(default_factory=tuple)
    stage_counts: dict[str, int] = Field(default_factory=dict)


class TsggUnifiedMetrics(BaseModel):
    """Unified TSGG metric bundle (state, causal, leakage, governance)."""

    model_config = ConfigDict(frozen=True)

    transition_precision: float = Field(ge=0.0, le=1.0)
    transition_recall: float = Field(ge=0.0, le=1.0)
    causal_path_completeness: float = Field(ge=0.0, le=1.0)
    leakage_score: float = Field(ge=0.0, le=1.0)
    procedural_independence: float = Field(ge=0.0, le=1.0)
    distributional_independence: float = Field(ge=0.0, le=1.0)
    governance_compliance_score: float = Field(ge=0.0, le=1.0)
    decision_traceability: float = Field(ge=0.0, le=1.0)
    tsgg_trust_index: float = Field(ge=0.0, le=1.0)


class TsggFrameworkReport(BaseModel):
    """Full TSGG framework evaluation."""

    model_config = ConfigDict(frozen=True)

    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    framework_name: str = "Trusted Safety State Governance Graph (TSGG)"
    pipeline_stages: tuple[TsggPipelineStage, ...]
    run_records: tuple[TsggRunRecord, ...] = Field(default_factory=tuple)
    unified_metrics: TsggUnifiedMetrics
    leakage_audit: LeakageAuditReport
    formulation_tex: str = ""
    figure_dot: str = ""
    disclaimer: str = Field(min_length=1)


TSGG_PIPELINE_CHAIN = (
    TsggPipelineStage.EVIDENCE,
    TsggPipelineStage.SAFETY_STATE,
    TsggPipelineStage.CAUSAL_TRANSITION,
    TsggPipelineStage.RECOMMENDATION,
    TsggPipelineStage.GOVERNANCE_DECISION,
    TsggPipelineStage.AUDIT_TRACE,
)

TSGG_DISCLAIMER = (
    "TSGG unified framework on synthetic confined-space harness. "
    "Integrates semantic state graph, causal attribution, benchmark leakage audit, "
    "and formal governance traces. Not a field certification."
)


__all__ = [
    "TSGG_DISCLAIMER",
    "TSGG_PIPELINE_CHAIN",
    "TsggFrameworkReport",
    "TsggPipelineStage",
    "TsggRunRecord",
    "TsggUnifiedMetrics",
]
