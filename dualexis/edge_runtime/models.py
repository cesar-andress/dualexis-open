"""Edge runtime domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dualexis.semantic_events.models import SemanticEvent


class EdgeNodeState(StrEnum):
    """Lifecycle state of an edge node process."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"


class EdgeZoneConfig(BaseModel):
    """Zone assignment for an edge capture node."""

    model_config = ConfigDict(frozen=True)

    zone_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)


class EdgePrivacyConfig(BaseModel):
    """Privacy settings embedded in edge node YAML."""

    model_config = ConfigDict(frozen=True)

    edge_buffer_ttl_seconds: int = Field(default=30, ge=1, le=300)
    allow_persistent_media: bool = False
    allow_biometric_features: bool = False
    allow_identity_linking: bool = False
    policy_id: str = Field(default="strict-v1", min_length=1, max_length=64)


class EdgeTransportConfig(BaseModel):
    """Event bus transport settings (reference manifest)."""

    model_config = ConfigDict(frozen=True)

    kind: str = Field(default="nats", min_length=1, max_length=16)
    url: str = Field(default="nats://localhost:4222", min_length=1, max_length=256)
    publish_subject_template: str = Field(
        default="dualexis.events.{site_id}.{zone_id}",
        min_length=1,
        max_length=256,
    )
    health_subject_template: str = Field(
        default="dualexis.health.{node_id}",
        min_length=1,
        max_length=256,
    )


class EdgeNodeConfig(BaseModel):
    """Full edge node manifest loaded from YAML."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    node_id: str = Field(min_length=1, max_length=64)
    site_id: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=512)
    zones: tuple[EdgeZoneConfig, ...] = Field(min_length=1)
    modalities: tuple[str, ...] = Field(min_length=1)
    privacy: EdgePrivacyConfig = Field(default_factory=EdgePrivacyConfig)
    transport: EdgeTransportConfig = Field(default_factory=EdgeTransportConfig)
    forbidden_egress_fields: tuple[str, ...] = Field(default_factory=tuple)


class GpuMetadata(BaseModel):
    """Optional GPU availability metadata (never required for operation)."""

    model_config = ConfigDict(frozen=True)

    available: bool = False
    device_name: str | None = None
    driver_version: str | None = None


class EdgeNodeStatus(BaseModel):
    """Operational status snapshot for CLI and control-plane consumers."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    site_id: str
    state: EdgeNodeState
    description: str
    zone_ids: tuple[str, ...]
    modalities: tuple[str, ...]
    policy_id: str
    gpu: GpuMetadata
    emissions_total: int = Field(ge=0)
    emissions_blocked: int = Field(ge=0)
    started_at: datetime | None = None


class EmissionBatch(BaseModel):
    """Result of a validated semantic event emission batch."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    scenario: str | None = None
    seed: int | None = None
    emitted_events: tuple[SemanticEvent, ...] = Field(default_factory=tuple)
    blocked_count: int = Field(default=0, ge=0)
    raw_media_blocked: bool = True


__all__ = [
    "EdgeNodeConfig",
    "EdgeNodeState",
    "EdgeNodeStatus",
    "EdgePrivacyConfig",
    "EdgeTransportConfig",
    "EdgeZoneConfig",
    "EmissionBatch",
    "GpuMetadata",
]
