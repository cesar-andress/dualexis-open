"""Edge runtime orchestration and configuration loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from dualexis.edge_runtime.health import HealthStatus, collect_health
from dualexis.edge_runtime.models import EdgeNodeConfig, EdgeNodeStatus, EmissionBatch
from dualexis.edge_runtime.node import EdgeNode
from dualexis.simulation import run_scenario


def default_node_config_path() -> Path:
    """Return the repository default edge node manifest path."""
    return Path(__file__).resolve().parent.parent.parent / "infrastructure" / "edge" / "node.yaml"


def load_edge_node_config(path: str | Path) -> EdgeNodeConfig:
    """Load and validate an edge node YAML manifest."""
    config_path = Path(path).resolve()
    if not config_path.is_file():
        msg = f"Edge node config not found: {config_path}"
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"Edge node config must be a YAML mapping: {config_path}"
        raise ValueError(msg)

    if isinstance(raw.get("zones"), list):
        raw["zones"] = tuple(raw["zones"])
    if isinstance(raw.get("modalities"), list):
        raw["modalities"] = tuple(raw["modalities"])
    if isinstance(raw.get("forbidden_egress_fields"), list):
        raw["forbidden_egress_fields"] = tuple(raw["forbidden_egress_fields"])

    return EdgeNodeConfig.model_validate(raw)


class EdgeRuntimeService:
    """Facade for edge node lifecycle, health, and synthetic emission."""

    def __init__(self, node: EdgeNode | None = None) -> None:
        self._node = node

    @property
    def node(self) -> EdgeNode | None:
        return self._node

    def run_node(self, config_path: str | Path) -> EdgeNode:
        """Load config and start an edge node process abstraction."""
        config = load_edge_node_config(config_path)
        node = EdgeNode(config)
        node.start()
        self._node = node
        return node

    def status(self) -> EdgeNodeStatus:
        """Return status for the active node or a stopped placeholder."""
        if self._node is None:
            config = load_edge_node_config(default_node_config_path())
            return EdgeNode(config).status()
        return self._node.status()

    def health(self) -> HealthStatus:
        """Collect health for the active node or a stopped placeholder."""
        if self._node is None:
            config = load_edge_node_config(default_node_config_path())
            return collect_health(EdgeNode(config))
        return collect_health(self._node)

    def emit_synthetic(
        self,
        scenario: str,
        *,
        seed: int = 42,
        config_path: str | Path | None = None,
    ) -> EmissionBatch:
        """Run a synthetic scenario and emit semantic events through the active node."""
        if self._node is None or self._node.state.value != "running":
            manifest = config_path or default_node_config_path()
            self.run_node(manifest)

        simulation = run_scenario(scenario, seed=seed)
        return self._node.emit_events(  # type: ignore[union-attr]
            simulation.events,
            scenario=scenario,
            seed=seed,
        )


# Module-level default service for CLI convenience
_default_service = EdgeRuntimeService()


def get_edge_runtime() -> EdgeRuntimeService:
    return _default_service


def run_node(config_path: str | Path) -> EdgeNode:
    return _default_service.run_node(config_path)


def edge_status() -> EdgeNodeStatus:
    return _default_service.status()


def edge_health() -> HealthStatus:
    return _default_service.health()


def emit_synthetic_events(
    scenario: str,
    *,
    seed: int = 42,
    config_path: str | Path | None = None,
) -> EmissionBatch:
    return _default_service.emit_synthetic(scenario, seed=seed, config_path=config_path)


__all__ = [
    "EdgeRuntimeService",
    "default_node_config_path",
    "edge_health",
    "edge_status",
    "emit_synthetic_events",
    "get_edge_runtime",
    "load_edge_node_config",
    "run_node",
]
