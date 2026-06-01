"""DUALEXIS edge runtime — node lifecycle, health, and semantic event emission."""

from __future__ import annotations

from dualexis.edge_runtime.health import HealthCheck, HealthStatus, collect_health
from dualexis.edge_runtime.models import (
    EdgeNodeConfig,
    EdgeNodeState,
    EdgeNodeStatus,
    EmissionBatch,
    GpuMetadata,
)
from dualexis.edge_runtime.node import EdgeNode, detect_gpu_metadata, privacy_policy_from_config
from dualexis.edge_runtime.service import (
    EdgeRuntimeService,
    default_node_config_path,
    edge_health,
    edge_status,
    emit_synthetic_events,
    get_edge_runtime,
    load_edge_node_config,
    run_node,
)

__all__ = [
    "EdgeNode",
    "EdgeNodeConfig",
    "EdgeNodeState",
    "EdgeNodeStatus",
    "EdgeRuntimeService",
    "EmissionBatch",
    "GpuMetadata",
    "HealthCheck",
    "HealthStatus",
    "collect_health",
    "default_node_config_path",
    "detect_gpu_metadata",
    "edge_health",
    "edge_status",
    "emit_synthetic_events",
    "get_edge_runtime",
    "load_edge_node_config",
    "privacy_policy_from_config",
    "run_node",
]
