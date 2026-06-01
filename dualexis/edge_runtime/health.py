"""Edge node health probes."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from dualexis.edge_runtime.models import EdgeNodeState, GpuMetadata
from dualexis.edge_runtime.node import EdgeNode
from dualexis.edge_runtime.telemetry import TelemetrySnapshot


class HealthCheck(BaseModel):
    """Single health probe result."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=64)
    status: str = Field(min_length=1, max_length=16)
    detail: str = Field(default="", max_length=512)


class HealthStatus(BaseModel):
    """Aggregate health report for an edge node."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    healthy: bool
    state: EdgeNodeState
    checks: tuple[HealthCheck, ...]
    gpu: GpuMetadata
    telemetry: TelemetrySnapshot
    generated_at: datetime


def collect_health(node: EdgeNode) -> HealthStatus:
    """Run health probes against a running or stopped edge node."""
    checks: list[HealthCheck] = []

    if node.state == EdgeNodeState.RUNNING:
        checks.append(
            HealthCheck(name="process", status="ok", detail="Edge node process is running")
        )
    elif node.state == EdgeNodeState.STOPPED:
        checks.append(HealthCheck(name="process", status="fail", detail="Edge node is not running"))
    else:
        checks.append(
            HealthCheck(name="process", status="degraded", detail=f"State={node.state.value}")
        )

    policy = node.privacy_runtime.active_policy()
    if not policy.allow_persistent_media and not policy.allow_biometric_features:
        checks.append(
            HealthCheck(name="privacy_policy", status="ok", detail=f"policy_id={policy.policy_id}")
        )
    else:
        checks.append(
            HealthCheck(
                name="privacy_policy",
                status="degraded",
                detail="Non-default privacy flags enabled",
            )
        )

    if node.config.zones:
        checks.append(
            HealthCheck(
                name="zones",
                status="ok",
                detail=f"{len(node.config.zones)} zone(s) configured",
            )
        )
    else:
        checks.append(HealthCheck(name="zones", status="fail", detail="No zones configured"))

    gpu = node.gpu_metadata
    gpu_detail = gpu.device_name or "CPU-only (GPU optional)"
    checks.append(HealthCheck(name="gpu", status="ok", detail=gpu_detail))

    healthy = node.state == EdgeNodeState.RUNNING and all(
        check.status == "ok" for check in checks if check.name != "gpu"
    )

    return HealthStatus(
        node_id=node.config.node_id,
        healthy=healthy,
        state=node.state,
        checks=tuple(checks),
        gpu=gpu,
        telemetry=node.telemetry.snapshot(),
        generated_at=datetime.now(tz=UTC),
    )


__all__ = ["HealthCheck", "HealthStatus", "collect_health"]
