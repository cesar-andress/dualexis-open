"""Privacy enforcement subsystem (legacy L1 adapters)."""

from dualexis.privacy.guard import DefaultPrivacyGuard
from dualexis.privacy.policies import DEFAULT_PRIVACY_POLICY, STRICT_PRIVACY_POLICY

__all__ = ["DEFAULT_PRIVACY_POLICY", "STRICT_PRIVACY_POLICY", "DefaultPrivacyGuard"]
