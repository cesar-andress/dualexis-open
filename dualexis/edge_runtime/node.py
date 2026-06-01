"""Edge node representation and event emission."""

from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.edge_runtime.models import (
    EdgeNodeConfig,
    EdgeNodeState,
    EdgeNodeStatus,
    EmissionBatch,
    GpuMetadata,
)
from dualexis.edge_runtime.telemetry import EdgeTelemetry
from dualexis.privacy_runtime.models import PrivacyPolicy, TrustBoundary
from dualexis.privacy_runtime.service import DefaultPrivacyRuntimeService
from dualexis.semantic_events.models import SemanticEvent


def detect_gpu_metadata() -> GpuMetadata:
    """Probe optional NVIDIA GPU availability without failing on CPU-only hosts."""
    if shutil.which("nvidia-smi") is None:
        return GpuMetadata(available=False)

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return GpuMetadata(available=False)

    if result.returncode != 0 or not result.stdout.strip():
        return GpuMetadata(available=False)

    first_line = result.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in first_line.split(",")]
    device_name = parts[0] if parts else None
    driver_version = parts[1] if len(parts) > 1 else None
    return GpuMetadata(available=True, device_name=device_name, driver_version=driver_version)


def privacy_policy_from_config(config: EdgeNodeConfig) -> PrivacyPolicy:
    """Build an L1 ``PrivacyPolicy`` from edge YAML privacy settings."""
    from datetime import timedelta

    privacy = config.privacy
    return PrivacyPolicy(
        policy_id=privacy.policy_id,
        name=f"Edge policy {privacy.policy_id}",
        allow_persistent_media=privacy.allow_persistent_media,
        allow_biometric_features=privacy.allow_biometric_features,
        allow_identity_linking=privacy.allow_identity_linking,
        max_buffer_ttl=timedelta(seconds=privacy.edge_buffer_ttl_seconds),
    )


class EdgeNode:
    """In-process edge node with privacy-gated semantic event emission."""

    def __init__(
        self,
        config: EdgeNodeConfig,
        *,
        privacy_runtime: DefaultPrivacyRuntimeService | None = None,
    ) -> None:
        self.config = config
        self.state = EdgeNodeState.STOPPED
        self.gpu_metadata = detect_gpu_metadata()
        self.telemetry = EdgeTelemetry()
        self._privacy = privacy_runtime or DefaultPrivacyRuntimeService(
            privacy_policy_from_config(config)
        )
        self._emitted_events: list[SemanticEvent] = []
        self._started_at: datetime | None = None

    @property
    def privacy_runtime(self) -> DefaultPrivacyRuntimeService:
        return self._privacy

    def start(self) -> None:
        """Transition the node to a running state."""
        self._privacy.reset_session_state()
        self.state = EdgeNodeState.RUNNING
        self._started_at = datetime.now(tz=UTC)

    def stop(self) -> None:
        """Transition the node to a stopped state."""
        self.state = EdgeNodeState.STOPPED

    def status(self) -> EdgeNodeStatus:
        """Return a serializable operational status snapshot."""
        snapshot = self.telemetry.snapshot()
        return EdgeNodeStatus(
            node_id=self.config.node_id,
            site_id=self.config.site_id,
            state=self.state,
            description=self.config.description,
            zone_ids=tuple(zone.zone_id for zone in self.config.zones),
            modalities=self.config.modalities,
            policy_id=self.config.privacy.policy_id,
            gpu=self.gpu_metadata,
            emissions_total=snapshot.emissions_total,
            emissions_blocked=snapshot.emissions_blocked,
            started_at=self._started_at,
        )

    def emit_event(self, event: SemanticEvent) -> SemanticEvent:
        """Validate and emit a semantic event; raw media is blocked by default."""
        if self.state != EdgeNodeState.RUNNING:
            msg = "Edge node must be running before emitting events"
            raise RuntimeError(msg)

        try:
            self._privacy.validate_semantic_event(event)
            payload = event.model_dump(mode="json")
            self._privacy.check_egress(payload, boundary=TrustBoundary.TB3_EVENT_PUBLICATION)
            self._assert_no_raw_media_metadata(event)
        except PrivacyViolationError:
            self.telemetry.record_blocked(raw_media=True)
            raise

        self._emitted_events.append(event)
        self.telemetry.record_emission()
        return event

    def emit_events(
        self,
        events: tuple[SemanticEvent, ...],
        *,
        scenario: str | None = None,
        seed: int | None = None,
    ) -> EmissionBatch:
        """Emit a batch of semantic events, counting blocked payloads."""
        emitted: list[SemanticEvent] = []
        blocked = 0
        for event in events:
            try:
                emitted.append(self.emit_event(event))
            except PrivacyViolationError:
                blocked += 1
        return EmissionBatch(
            node_id=self.config.node_id,
            scenario=scenario,
            seed=seed,
            emitted_events=tuple(emitted),
            blocked_count=blocked,
            raw_media_blocked=True,
        )

    def emitted_events(self) -> tuple[SemanticEvent, ...]:
        return tuple(self._emitted_events)

    @staticmethod
    def _assert_no_raw_media_metadata(event: SemanticEvent) -> None:
        forbidden_fragments = ("raw_video", "raw_audio", "image_data", "payload_ref")
        for key, value in event.metadata.items():
            normalized_key = key.lower()
            if any(fragment in normalized_key for fragment in forbidden_fragments):
                msg = f"Raw media metadata key '{key}' is prohibited on edge egress"
                raise PrivacyViolationError(msg)
            if any(fragment in value.lower() for fragment in forbidden_fragments):
                msg = f"Raw media metadata value in '{key}' is prohibited on edge egress"
                raise PrivacyViolationError(msg)


__all__ = [
    "EdgeNode",
    "detect_gpu_metadata",
    "privacy_policy_from_config",
]
