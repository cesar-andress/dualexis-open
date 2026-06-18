"""Benchmark manifest loading and hash verification."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ManifestFileHash(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class ManifestArtefactHashes(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    files: tuple[ManifestFileHash, ...] = Field(default_factory=tuple)


class BenchmarkManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_version: str
    generated_for_release: str
    description: str = ""
    evaluation_seeds: tuple[int, ...]
    calibration_seeds: tuple[int, ...]
    ground_truth_rules: ManifestArtefactHashes
    emission_profiles: ManifestArtefactHashes
    target_par_band: tuple[float, float]
    target_fpr_band: tuple[float, float]
    target_fnr_band: tuple[float, float]
    target_ls_max: float = 0.55
    shared_threshold_ratio_max: float = 0.35


def default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "experiments" / "benchmark_manifest.yaml"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def load_benchmark_manifest(path: Path | None = None) -> BenchmarkManifest:
    manifest_path = path or default_manifest_path()
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return BenchmarkManifest.model_validate(raw)


@dataclass(frozen=True)
class ManifestVerificationResult:
    ok: bool
    mismatches: tuple[str, ...]


def verify_benchmark_manifest(path: Path | None = None) -> ManifestVerificationResult:
    """Verify on-disk artefact hashes against the manifest."""
    manifest = load_benchmark_manifest(path)
    root = repo_root()
    mismatches: list[str] = []

    for section in (manifest.ground_truth_rules, manifest.emission_profiles):
        for entry in section.files:
            file_path = root / entry.path
            if not file_path.is_file():
                mismatches.append(f"missing: {entry.path}")
                continue
            actual = sha256_file(file_path)
            if actual != entry.sha256:
                mismatches.append(
                    f"hash mismatch: {entry.path} expected={entry.sha256[:12]}… "
                    f"actual={actual[:12]}…"
                )

    return ManifestVerificationResult(ok=not mismatches, mismatches=tuple(mismatches))


__all__ = [
    "BenchmarkManifest",
    "ManifestVerificationResult",
    "default_manifest_path",
    "load_benchmark_manifest",
    "repo_root",
    "sha256_file",
    "verify_benchmark_manifest",
]
