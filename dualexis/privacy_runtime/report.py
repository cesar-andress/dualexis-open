"""Privacy report generation for L1 runtime and pipeline outputs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from dualexis.privacy_runtime.models import PrivacyPolicy, PrivacyViolation


class PrivacyReport(BaseModel):
    """Privacy posture summary for a runtime session or pipeline run."""

    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(min_length=1, max_length=64)
    raw_video_retention_seconds: int = Field(default=0, ge=0)
    raw_audio_retention_seconds: int = Field(default=0, ge=0)
    semantic_event_retention_days: int = Field(default=30, ge=1)
    raw_media_persisted: bool = False
    raw_media_bytes_persisted: int = Field(default=0, ge=0)
    personal_data_violations: int = Field(default=0, ge=0)
    violations: tuple[PrivacyViolation, ...] = Field(default_factory=tuple)
    trust_boundaries_passed: tuple[str, ...] = Field(default_factory=tuple)
    policy_compliant: bool = True
    high_risk_audit_satisfied: bool = True
    evaluation_metrics: object | None = None


def build_privacy_report(
    policy: PrivacyPolicy,
    *,
    violations: tuple[PrivacyViolation, ...] = (),
    trust_boundaries_passed: tuple[str, ...] = (),
    raw_media_persisted: bool = False,
    raw_media_bytes_persisted: int = 0,
    high_risk_audit_satisfied: bool = True,
    evaluation_metrics: object | None = None,
) -> PrivacyReport:
    """Build a ``PrivacyReport`` from runtime enforcement state."""
    violation_count = len(violations)
    policy_compliant = (
        violation_count == 0
        and not raw_media_persisted
        and raw_media_bytes_persisted == 0
        and high_risk_audit_satisfied
    )
    return PrivacyReport(
        policy_id=policy.policy_id,
        raw_video_retention_seconds=policy.raw_video_retention_seconds,
        raw_audio_retention_seconds=policy.raw_audio_retention_seconds,
        semantic_event_retention_days=policy.semantic_event_retention_days,
        raw_media_persisted=raw_media_persisted,
        raw_media_bytes_persisted=raw_media_bytes_persisted,
        personal_data_violations=violation_count,
        violations=violations,
        trust_boundaries_passed=trust_boundaries_passed,
        policy_compliant=policy_compliant,
        high_risk_audit_satisfied=high_risk_audit_satisfied,
        evaluation_metrics=evaluation_metrics,
    )


__all__ = ["PrivacyReport", "build_privacy_report"]
