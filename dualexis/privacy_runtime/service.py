"""L1 Privacy Runtime Layer — enforcement service and payload utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.orchestration.models import HIGH_RISK_SEVERITIES
from dualexis.privacy_runtime.interfaces import PrivacyRuntimeService
from dualexis.privacy_runtime.models import (
    FORBIDDEN_MEDIA_FIELDS,
    MEDIA_STRIP_FIELDS,
    PrivacyCheckResult,
    PrivacyPolicy,
    PrivacyViolation,
    PrivacyViolationType,
    RetentionDecision,
    TrustBoundary,
    classify_forbidden_field,
    is_forbidden_field,
    normalize_field_key,
)
from dualexis.privacy_runtime.policies import DEFAULT_PRIVACY_POLICY
from dualexis.privacy_runtime.report import PrivacyReport, build_privacy_report
from dualexis.schemas.audit import AuditEntry
from dualexis.schemas.domain import SafetyEvent
from dualexis.schemas.perception import PerceptionFrame, PerceptionSignal


def validate_payload_privacy(
    payload: Mapping[str, Any],
    policy: PrivacyPolicy,
    *,
    boundary: TrustBoundary | None = None,
) -> None:
    """Validate a nested payload mapping against privacy policy constraints.

    Raises ``PrivacyViolationError`` on the first forbidden field (fail-closed).
    """
    for key, value in payload.items():
        key_str = str(key)
        normalized = normalize_field_key(key_str)
        if is_forbidden_field(key_str):
            if normalized == "payload_ref" and value in (None, ""):
                continue
            violation_type = classify_forbidden_field(key_str)
            boundary_label = boundary.value if boundary is not None else "unspecified"
            msg = f"Forbidden {violation_type.value} field '{key_str}' at boundary {boundary_label}"
            raise PrivacyViolationError(msg)
        if (
            normalized in FORBIDDEN_MEDIA_FIELDS
            and value not in (None, "")
            and not policy.allow_persistent_media
        ):
            msg = (
                f"Persistent media reference '{key_str}' is prohibited "
                "unless allow_persistent_media is enabled"
            )
            raise PrivacyViolationError(msg)
        if isinstance(value, dict):
            validate_payload_privacy(value, policy, boundary=boundary)


def strip_raw_media(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of *payload* with raw media keys removed."""
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        normalized = normalize_field_key(str(key))
        if normalized in MEDIA_STRIP_FIELDS:
            continue
        if isinstance(value, dict):
            sanitized[str(key)] = strip_raw_media(value)
        else:
            sanitized[str(key)] = value
    return sanitized


def enforce_retention_policy(
    policy: PrivacyPolicy,
    *,
    artifact_kind: str,
    created_at: datetime | None = None,
) -> RetentionDecision:
    """Compute whether an artifact may be retained under *policy*."""
    _ = created_at or datetime.now(tz=UTC)
    kind = artifact_kind.lower()
    if kind in {"raw_video", "video", "frame", "perception_frame"}:
        seconds = policy.raw_video_retention_seconds
        may_retain = policy.allow_persistent_media and seconds > 0
        return RetentionDecision(
            artifact_kind=artifact_kind,
            may_retain=may_retain,
            retention_seconds=seconds,
            reason="Raw video retention defaults to zero unless explicitly allowed",
        )
    if kind in {"raw_audio", "audio"}:
        seconds = policy.raw_audio_retention_seconds
        may_retain = policy.allow_persistent_media and seconds > 0
        return RetentionDecision(
            artifact_kind=artifact_kind,
            may_retain=may_retain,
            retention_seconds=seconds,
            reason="Raw audio retention defaults to zero unless explicitly allowed",
        )
    if kind in {"semantic_event", "safety_event", "event"}:
        days = policy.semantic_event_retention_days
        return RetentionDecision(
            artifact_kind=artifact_kind,
            may_retain=True,
            retention_seconds=days * 86_400,
            reason="Semantic events may be retained according to policy",
        )
    if kind == "audit":
        days = policy.audit_retention_days
        return RetentionDecision(
            artifact_kind=artifact_kind,
            may_retain=True,
            retention_seconds=days * 86_400,
            reason="Audit metadata retained per audit_retention_days",
        )
    return RetentionDecision(
        artifact_kind=artifact_kind,
        may_retain=False,
        retention_seconds=0,
        reason="Unknown artifact kind — retention denied by default",
    )


def _is_persistent_media_reference(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if lowered.startswith(("http://", "https://", "file://", "s3://")):
        return True
    return "/" in value or "\\" in value


class DefaultPrivacyRuntimeService(PrivacyRuntimeService):
    """Enforces privacy policy at runtime trust boundaries TB1--TB5."""

    def __init__(self, policy: PrivacyPolicy | None = None) -> None:
        self._policy = policy or DEFAULT_PRIVACY_POLICY
        self._violations: list[PrivacyViolation] = []
        self._trust_boundaries: list[str] = []
        self._raw_media_persisted = False
        self._raw_media_bytes_persisted = 0

    def active_policy(self) -> PrivacyPolicy:
        return self._policy

    def reset_session_state(self) -> None:
        """Clear per-run violation and boundary tracking."""
        self._violations.clear()
        self._trust_boundaries.clear()
        self._raw_media_persisted = False
        self._raw_media_bytes_persisted = 0

    def record_boundary(self, boundary: TrustBoundary) -> None:
        if boundary.value not in self._trust_boundaries:
            self._trust_boundaries.append(boundary.value)

    def validate_frame(self, frame: PerceptionFrame) -> PrivacyCheckResult:
        payload = frame.model_dump(mode="python")
        if frame.payload_ref is not None and _is_persistent_media_reference(frame.payload_ref):
            if not self._policy.allow_persistent_media:
                self._fail(
                    field_name="payload_ref",
                    violation_type=PrivacyViolationType.MEDIA,
                    message="Persistent media paths are prohibited by default policy",
                    boundary=TrustBoundary.TB1_EPHEMERAL_BUFFER,
                )
            self._raw_media_persisted = True
        self._validate_payload_guarded(payload, TrustBoundary.TB1_EPHEMERAL_BUFFER)
        self.record_boundary(TrustBoundary.TB1_EPHEMERAL_BUFFER)
        return PrivacyCheckResult.PASSED

    def sanitize_frame(self, frame: PerceptionFrame) -> PerceptionFrame:
        """Return an ephemeral frame with raw media references stripped."""
        sanitized = strip_raw_media(frame.model_dump(mode="python"))
        sanitized["payload_ref"] = None
        return PerceptionFrame.model_validate(sanitized)

    def validate_signal(self, signal: PerceptionSignal) -> PerceptionSignal:
        if self._policy.allow_biometric_features:
            self._fail(
                field_name="allow_biometric_features",
                violation_type=PrivacyViolationType.BIOMETRIC,
                message="Biometric features are prohibited",
                boundary=TrustBoundary.TB2_PERCEPTION_OUTPUT,
            )

        payload = signal.model_dump(mode="python")
        self._validate_payload_guarded(payload, TrustBoundary.TB2_PERCEPTION_OUTPUT)

        sanitized_features = strip_raw_media(signal.features)
        self.record_boundary(TrustBoundary.TB2_PERCEPTION_OUTPUT)
        if sanitized_features != signal.features:
            return signal.model_copy(update={"features": sanitized_features})
        return signal

    def validate_event(self, event: SafetyEvent) -> SafetyEvent:
        for descriptor in event.descriptors:
            self._validate_payload_guarded(
                descriptor.evidence,
                TrustBoundary.TB3_EVENT_PUBLICATION,
            )

        metadata = getattr(event, "metadata", None)
        if isinstance(metadata, dict):
            self._validate_payload_guarded(metadata, TrustBoundary.TB3_EVENT_PUBLICATION)

        try:
            payload = event.model_dump(mode="python")
            self._validate_payload_guarded(payload, TrustBoundary.TB3_EVENT_PUBLICATION)
        except AttributeError:
            pass

        decision = enforce_retention_policy(
            self._policy,
            artifact_kind="semantic_event",
            created_at=event.timestamp,
        )
        if not decision.may_retain:
            self._fail(
                field_name="semantic_event",
                violation_type=PrivacyViolationType.POLICY,
                message="Semantic event retention denied by active policy",
                boundary=TrustBoundary.TB3_EVENT_PUBLICATION,
            )

        self.record_boundary(TrustBoundary.TB3_EVENT_PUBLICATION)
        return event

    def validate_semantic_event(self, event: object) -> object:
        """Validate a domain ``SemanticEvent`` before graph/reasoning stages."""
        if not hasattr(event, "model_dump"):
            msg = "Expected a Pydantic semantic event model"
            raise TypeError(msg)
        payload = cast(Any, event).model_dump(mode="python")
        self._validate_payload_guarded(payload, TrustBoundary.TB3_EVENT_PUBLICATION)
        self.record_boundary(TrustBoundary.TB3_EVENT_PUBLICATION)
        return event

    def check_egress(
        self,
        payload: dict[str, object],
        *,
        boundary: TrustBoundary,
    ) -> PrivacyCheckResult:
        normalized = {str(key): value for key, value in payload.items()}
        self._validate_payload_guarded(normalized, boundary)
        self.record_boundary(boundary)
        return PrivacyCheckResult.PASSED

    def ensure_high_risk_audit(
        self,
        events: Sequence[object],
        audit_records: Sequence[AuditEntry],
    ) -> None:
        """Require audit records when high-risk events are present."""

        def _severity_value(event: object) -> str | None:
            severity = getattr(event, "severity", None)
            if severity is None:
                return None
            value = getattr(severity, "value", None)
            if isinstance(value, str):
                return value
            return str(severity)

        high_risk_present = any(
            (severity_value := _severity_value(event)) is not None
            and severity_value in HIGH_RISK_SEVERITIES
            for event in events
        )
        if not high_risk_present:
            return
        if not audit_records:
            self._fail(
                field_name="audit_records",
                violation_type=PrivacyViolationType.AUDIT,
                message="High-risk events require audit records",
                boundary=TrustBoundary.TB3_EVENT_PUBLICATION,
            )

    def buffer_expired(
        self, frame: PerceptionFrame, *, observed_at: datetime | None = None
    ) -> bool:
        """Return whether an ephemeral frame exceeded policy buffer TTL (TB1)."""
        now = observed_at or datetime.now(tz=UTC)
        age = now - frame.timestamp
        return age > self._policy.max_buffer_ttl

    def retention_expires_at(self, *, created_at: datetime) -> datetime:
        """Compute semantic event metadata retention horizon."""
        delta = timedelta(days=self._policy.semantic_event_retention_days)
        return created_at + delta

    def _validate_payload_guarded(
        self,
        payload: Mapping[str, Any],
        boundary: TrustBoundary,
    ) -> None:
        try:
            validate_payload_privacy(payload, self._policy, boundary=boundary)
        except PrivacyViolationError as exc:
            field_name = self._first_forbidden_key(payload) or "payload"
            self._fail(
                field_name=field_name,
                violation_type=classify_forbidden_field(field_name),
                message=str(exc),
                boundary=boundary,
            )

    @staticmethod
    def _first_forbidden_key(payload: Mapping[str, Any]) -> str | None:
        for key, value in payload.items():
            key_str = str(key)
            if is_forbidden_field(key_str):
                if normalize_field_key(key_str) == "payload_ref" and value in (None, ""):
                    continue
                return key_str
            if isinstance(value, dict):
                nested = DefaultPrivacyRuntimeService._first_forbidden_key(value)
                if nested is not None:
                    return nested
        return None

    def build_report(
        self,
        *,
        high_risk_audit_satisfied: bool = True,
        evaluation_metrics: object | None = None,
    ) -> PrivacyReport:
        """Build a privacy report for the current runtime session."""
        return build_privacy_report(
            self._policy,
            violations=tuple(self._violations),
            trust_boundaries_passed=tuple(self._trust_boundaries),
            raw_media_persisted=self._raw_media_persisted,
            raw_media_bytes_persisted=self._raw_media_bytes_persisted,
            high_risk_audit_satisfied=high_risk_audit_satisfied,
            evaluation_metrics=evaluation_metrics,
        )

    def _fail(
        self,
        *,
        field_name: str,
        violation_type: PrivacyViolationType,
        message: str,
        boundary: TrustBoundary | None,
    ) -> None:
        violation = PrivacyViolation(
            field_name=field_name,
            violation_type=violation_type,
            message=message,
            boundary=boundary.value if boundary is not None else None,
        )
        self._violations.append(violation)
        raise PrivacyViolationError(message)


PlaceholderPrivacyRuntimeService = DefaultPrivacyRuntimeService


__all__ = [
    "DefaultPrivacyRuntimeService",
    "PlaceholderPrivacyRuntimeService",
    "enforce_retention_policy",
    "strip_raw_media",
    "validate_payload_privacy",
]
