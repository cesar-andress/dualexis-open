"""Export measurement artifacts to the results/ directory tree."""

from __future__ import annotations

import json
from pathlib import Path

from dualexis.measurement.models import CombinedMeasurementReport, MeasurementReport

RESULTS_SUBDIRS: tuple[str, ...] = ("measurements", "experiments", "reports")


def repo_root() -> Path:
    """Return the repository root (parent of the ``dualexis`` package)."""
    return Path(__file__).resolve().parent.parent.parent


def default_results_root() -> Path:
    """Default ``results/`` directory at repository root."""
    return repo_root() / "results"


def ensure_results_layout(results_root: Path | None = None) -> Path:
    """Create ``results/`` and standard subdirectories if missing."""
    root = (results_root or default_results_root()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in RESULTS_SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def resolve_output_path(path: str | Path, *, subdir: str = "measurements") -> Path:
    """Resolve CLI output paths relative to the current working directory."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()

    if len(candidate.parts) == 1:
        root = ensure_results_layout(Path.cwd() / "results")
        return (root / subdir / candidate).resolve()

    resolved = (Path.cwd() / candidate).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def write_measurement_json(report: MeasurementReport, path: Path) -> Path:
    """Write a measurement report as JSON, creating parent directories safely."""
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


def write_combined_json(report: CombinedMeasurementReport, path: Path) -> Path:
    """Write a combined ``measure all`` report as JSON."""
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


__all__ = [
    "RESULTS_SUBDIRS",
    "default_results_root",
    "ensure_results_layout",
    "repo_root",
    "resolve_output_path",
    "write_combined_json",
    "write_measurement_json",
]
