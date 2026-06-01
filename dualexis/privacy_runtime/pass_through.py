"""Pass-through privacy runtime for ablation experiments (L1 disabled)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from dualexis.privacy_runtime.interfaces import PrivacyRuntimeService
from dualexis.privacy_runtime.models import PrivacyCheckResult, PrivacyPolicy, TrustBoundary
from dualexis.privacy_runtime.policies import DEFAULT_PRIVACY_POLICY
from dualexis.privacy_runtime.report import PrivacyReport, build_privacy_report
from dualexis.schemas.audit import AuditEntry
from dualexis.schemas.domain import SafetyEvent
from dualexis.schemas.perception import PerceptionFrame, PerceptionSignal


class PassThroughPrivacyRuntimeService(PrivacyRuntimeService):
    """Ablation stub: does not enforce privacy policy (records zero violations)."""

    def __init__(self, policy: PrivacyPolicy | None = None) -> None:
        self._policy = policy or DEFAULT_PRIVACY_POLICY

    def active_policy(self) -> PrivacyPolicy:
        return self._policy

    def reset_session_state(self) -> None:
        return None

    def validate_frame(self, frame: PerceptionFrame) -> PrivacyCheckResult:
        return PrivacyCheckResult.PASSED

    def sanitize_frame(self, frame: PerceptionFrame) -> PerceptionFrame:
        return frame

    def validate_signal(self, signal: PerceptionSignal) -> PerceptionSignal:
        return signal

    def validate_event(self, event: SafetyEvent) -> SafetyEvent:
        return event

    def check_egress(
        self, payload: dict[str, object], *, boundary: TrustBoundary
    ) -> PrivacyCheckResult:
        return PrivacyCheckResult.PASSED

    def ensure_high_risk_audit(
        self,
        events: Sequence[object],
        audit_records: Sequence[AuditEntry],
    ) -> None:
        return None

    def buffer_expired(
        self, frame: PerceptionFrame, *, observed_at: datetime | None = None
    ) -> bool:
        return False

    def build_report(
        self,
        *,
        high_risk_audit_satisfied: bool = True,
        evaluation_metrics: object | None = None,
    ) -> PrivacyReport:
        return build_privacy_report(
            self._policy,
            violations=(),
            trust_boundaries_passed=(),
            raw_media_persisted=False,
            raw_media_bytes_persisted=0,
            high_risk_audit_satisfied=high_risk_audit_satisfied,
            evaluation_metrics=evaluation_metrics,
        )


__all__ = ["PassThroughPrivacyRuntimeService"]
