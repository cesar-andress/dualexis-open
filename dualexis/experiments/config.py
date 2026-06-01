"""YAML experiment configuration loading."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from dualexis.evaluation.protocol import ExperimentProtocolId


class ExperimentConfig(BaseModel):
    """Declarative battery configuration loaded from YAML."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str = Field(min_length=1, max_length=64)
    scenario: str = Field(min_length=1, max_length=64)
    seed: int = 42
    protocol: str = Field(default=ExperimentProtocolId.DUALEXIS_FULL_PIPELINE.value)
    latency_runs: int = Field(default=5, ge=1, le=100)
    robustness_runs: int = Field(default=1, ge=1, le=100)
    drop_modality: str = Field(default="audio", min_length=1, max_length=32)
    description: str = Field(default="", max_length=512)


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    """Load and validate an experiment battery configuration file."""
    config_path = Path(path).resolve()
    if not config_path.is_file():
        msg = f"Experiment config not found: {config_path}"
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"Experiment config must be a YAML mapping: {config_path}"
        raise ValueError(msg)

    return ExperimentConfig.model_validate(raw)


def default_config_dir() -> Path:
    """Return the repository ``configs/`` directory."""
    return Path(__file__).resolve().parent.parent.parent / "configs"


def list_experiment_configs(config_dir: Path | None = None) -> tuple[Path, ...]:
    """Return sorted YAML config paths under ``configs/``."""
    root = config_dir or default_config_dir()
    if not root.is_dir():
        msg = f"Experiment config directory not found: {root}"
        raise FileNotFoundError(msg)
    return tuple(sorted(root.glob("*.yaml")))


__all__ = [
    "ExperimentConfig",
    "default_config_dir",
    "list_experiment_configs",
    "load_experiment_config",
]
