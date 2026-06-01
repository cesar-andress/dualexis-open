"""Built-in privacy policies for L1 Privacy Runtime Layer."""

from __future__ import annotations

from datetime import timedelta

from dualexis.privacy_runtime.models import PrivacyPolicy
from dualexis.schemas.domain.enums import RetentionPolicy as EventRetentionTier

STRICT_PRIVACY_POLICY = PrivacyPolicy(
    policy_id="strict-v1",
    name="Strict Privacy (Default)",
    raw_video_retention_seconds=0,
    raw_audio_retention_seconds=0,
    semantic_event_retention_days=30,
    audit_retention_days=365,
    allow_persistent_media=False,
    allow_biometric_features=False,
    allow_identity_linking=False,
    allow_cross_zone_tracking=False,
    max_buffer_ttl=timedelta(seconds=30),
    event_retention=EventRetentionTier.STANDARD,
)

DEFAULT_PRIVACY_POLICY = STRICT_PRIVACY_POLICY

__all__ = ["DEFAULT_PRIVACY_POLICY", "STRICT_PRIVACY_POLICY"]
