"""Default privacy guard enforcing policy constraints at the edge (L1 adapter)."""

from __future__ import annotations

from dualexis.core.interfaces import PrivacyGuard
from dualexis.privacy_runtime.models import FORBIDDEN_FIELDS
from dualexis.privacy_runtime.service import DefaultPrivacyRuntimeService
from dualexis.schemas.domain import SafetyEvent
from dualexis.schemas.perception import PerceptionSignal
from dualexis.schemas.privacy import PrivacyPolicy

FORBIDDEN_FEATURE_KEYS = frozenset(FORBIDDEN_FIELDS)


class DefaultPrivacyGuard(PrivacyGuard):
    """Legacy PrivacyGuard adapter delegating to L1 Privacy Runtime Service."""

    def __init__(self, policy: PrivacyPolicy | None = None) -> None:
        self._runtime = DefaultPrivacyRuntimeService(policy)

    def validate_signal(self, signal: PerceptionSignal) -> PerceptionSignal:
        return self._runtime.validate_signal(signal)

    def validate_event(self, event: SafetyEvent) -> SafetyEvent:
        return self._runtime.validate_event(event)

    def active_policy(self) -> PrivacyPolicy:
        return self._runtime.active_policy()
