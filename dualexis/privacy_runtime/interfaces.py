"""L1 Privacy Runtime Layer — service interfaces.

Maps to DUALEXIS Framework Layer 1 (Privacy Runtime Layer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from dualexis.privacy_runtime.models import PrivacyCheckResult, PrivacyPolicy, TrustBoundary
from dualexis.privacy_runtime.report import PrivacyReport
from dualexis.schemas.audit import AuditEntry
from dualexis.schemas.domain import SafetyEvent
from dualexis.schemas.perception import PerceptionFrame, PerceptionSignal


class PrivacyRuntimeService(ABC):
    """Cross-cutting privacy enforcement across all framework layers."""

    @abstractmethod
    def active_policy(self) -> PrivacyPolicy:
        """Return the currently enforced privacy policy."""

    @abstractmethod
    def validate_frame(self, frame: PerceptionFrame) -> PrivacyCheckResult:
        """Validate ephemeral frame constraints (TB1)."""

    @abstractmethod
    def sanitize_frame(self, frame: PerceptionFrame) -> PerceptionFrame:
        """Return an ephemeral frame with raw media references stripped (TB1)."""

    @abstractmethod
    def validate_signal(self, signal: PerceptionSignal) -> PerceptionSignal:
        """Validate perception output before fusion (TB2)."""

    @abstractmethod
    def validate_event(self, event: SafetyEvent) -> SafetyEvent:
        """Validate structured event before graph/reasoning/publish (TB3)."""

    @abstractmethod
    def check_egress(
        self, payload: dict[str, object], *, boundary: TrustBoundary
    ) -> PrivacyCheckResult:
        """Validate payload before network or LLM egress (TB4/TB5)."""

    @abstractmethod
    def build_report(
        self,
        *,
        high_risk_audit_satisfied: bool = True,
        evaluation_metrics: object | None = None,
    ) -> PrivacyReport:
        """Build a privacy report for the current runtime session."""

    @abstractmethod
    def ensure_high_risk_audit(
        self,
        events: Sequence[object],
        audit_records: Sequence[AuditEntry],
    ) -> None:
        """Verify audit coverage for high-risk events."""

    @abstractmethod
    def buffer_expired(
        self, frame: PerceptionFrame, *, observed_at: datetime | None = None
    ) -> bool:
        """Return whether an ephemeral frame exceeded policy buffer TTL."""
