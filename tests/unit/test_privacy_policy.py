"""Tests for privacy policy schema validation."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from dualexis.privacy.policies import DEFAULT_PRIVACY_POLICY, STRICT_PRIVACY_POLICY
from dualexis.schemas.domain import RetentionPolicy
from dualexis.schemas.privacy import PrivacyPolicy


@pytest.mark.unit
def test_strict_privacy_policy_validates() -> None:
    policy = PrivacyPolicy(
        policy_id="strict-test",
        name="Strict Test Policy",
        allow_persistent_media=False,
        allow_biometric_features=False,
        allow_identity_linking=False,
        allow_cross_zone_tracking=False,
        max_buffer_ttl=timedelta(seconds=30),
        event_retention=RetentionPolicy.STANDARD,
    )
    assert policy.policy_id == "strict-test"
    assert policy.max_buffer_ttl == timedelta(seconds=30)


@pytest.mark.unit
def test_builtin_strict_policy_is_default() -> None:
    assert DEFAULT_PRIVACY_POLICY.policy_id == STRICT_PRIVACY_POLICY.policy_id
    assert DEFAULT_PRIVACY_POLICY.allow_biometric_features is False
    assert DEFAULT_PRIVACY_POLICY.allow_persistent_media is False


@pytest.mark.unit
def test_privacy_policy_rejects_biometric_features() -> None:
    with pytest.raises(ValidationError, match="Biometric"):
        PrivacyPolicy(
            policy_id="invalid",
            name="Invalid Policy",
            allow_biometric_features=True,
        )


@pytest.mark.unit
def test_privacy_policy_rejects_long_ttl_with_persistent_media() -> None:
    with pytest.raises(ValidationError, match="buffer TTL"):
        PrivacyPolicy(
            policy_id="invalid-media",
            name="Invalid Media Policy",
            allow_persistent_media=True,
            max_buffer_ttl=timedelta(minutes=10),
        )
