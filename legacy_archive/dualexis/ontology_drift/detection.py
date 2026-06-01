"""Ontology drift detection orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dualexis.core.version import get_version
from dualexis.experiments.sssg_battery import PAPER_SCENARIOS
from dualexis.ontology_drift.metrics import (
    aggregate_report_metrics,
    cross_version_vocab_drift,
    scenario_drift_metrics,
    summarize_version,
)
from dualexis.ontology_drift.models import OntologyDriftReport
from dualexis.ontology_drift.snapshots import collect_snapshot_grid

ONTOLOGY_DRIFT_DISCLAIMER = (
    "Ontology drift audit on synthetic benchmark runs. Measures stability of semantic labels, "
    "safety states, and recommendations across scenarios, seeds, and package versions. "
    "Does not attest field semantic interoperability."
)


def run_ontology_drift_detection(
    *,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3, 4, 5),
    versions: tuple[str, ...] | None = None,
    registry_dir: Path | None = None,
) -> OntologyDriftReport:
    """
    Detect ontology drift across scenarios, seeds, and benchmark versions.

    ``versions`` defaults to the current package version. Prior version vocabularies
    are loaded from ``registry_dir`` when present for cross-version comparison.
    """
    current_version = get_version()
    version_list = versions or (current_version,)
    all_snapshots: list = []
    registry_warnings: list[str] = []

    for version in version_list:
        if version == current_version:
            all_snapshots.extend(collect_snapshot_grid(scenarios, seeds, version=version))
        elif registry_dir is not None:
            loaded = _load_version_snapshots(registry_dir, version, scenarios, seeds)
            if loaded:
                all_snapshots.extend(loaded)
            else:
                registry_path = registry_dir / f"vocabulary_{version}.json"
                if registry_path.is_file():
                    registry_warnings.append(
                        f"Registry {registry_path} has no cells for requested scenarios/seeds; "
                        f"cross-version metrics exclude {version}."
                    )
                else:
                    registry_warnings.append(
                        f"Missing registry {registry_path}; run ontology-drift on package "
                        f"{version} and export to populate it before comparing versions."
                    )
        else:
            registry_warnings.append(
                f"Version {version} is not current ({current_version}) and no registry_dir "
                "was provided; cannot load historical snapshots."
            )

    if not all_snapshots:
        all_snapshots = list(collect_snapshot_grid(scenarios, seeds, version=current_version))

    primary_version = current_version if current_version in version_list else version_list[0]

    per_scenario = [
        scenario_drift_metrics(all_snapshots, scenario_id=scenario, version=primary_version)
        for scenario in scenarios
    ]

    version_summaries = [summarize_version(all_snapshots, version) for version in version_list]
    if current_version not in {summary.version for summary in version_summaries}:
        version_summaries.append(summarize_version(all_snapshots, current_version))

    ontology_stability, semantic_drift, recommendation_drift = aggregate_report_metrics(
        per_scenario
    )

    cross_version_semantic = 0.0
    comparable = [summary for summary in version_summaries if summary.snapshot_count > 0]
    if len(comparable) >= 2:
        ordered = sorted(comparable, key=lambda item: item.version)
        label_drifts: list[float] = []
        for index in range(len(ordered) - 1):
            ld, _, _ = cross_version_vocab_drift(ordered[index], ordered[index + 1])
            label_drifts.append(ld)
        cross_version_semantic = round(
            sum(label_drifts) / len(label_drifts) if label_drifts else 0.0,
            4,
        )
    elif len(version_list) >= 2 and len(comparable) < 2:
        registry_warnings.append(
            "Cross-version semantic drift not computed: fewer than two versions have "
            "populated registry snapshots."
        )

    return OntologyDriftReport(
        generated_at=datetime.now(tz=UTC),
        versions=tuple(sorted({s.version for s in all_snapshots})),
        seeds=seeds,
        scenarios=scenarios,
        snapshots=tuple(all_snapshots),
        per_scenario=tuple(per_scenario),
        version_summaries=tuple(version_summaries),
        ontology_stability=ontology_stability,
        semantic_drift=semantic_drift,
        recommendation_drift=recommendation_drift,
        cross_version_semantic_drift=cross_version_semantic,
        registry_warnings=tuple(registry_warnings),
        disclaimer=ONTOLOGY_DRIFT_DISCLAIMER,
    )


def _load_version_snapshots(
    registry_dir: Path,
    version: str,
    scenarios: tuple[str, ...],
    seeds: tuple[int, ...],
) -> list:
    from dualexis.ontology_drift.models import OntologySnapshot

    path = registry_dir / f"vocabulary_{version}.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshots: list[OntologySnapshot] = []
    for scenario in scenarios:
        for seed in seeds:
            cell = payload.get("cells", {}).get(f"{scenario}:{seed}")
            if cell:
                snapshots.append(OntologySnapshot.model_validate(cell))
    return snapshots


def persist_version_vocabulary(
    report: OntologyDriftReport,
    registry_dir: Path,
) -> None:
    """Save per-version vocabulary for future cross-version drift audits."""
    registry_dir.mkdir(parents=True, exist_ok=True)
    for summary in report.version_summaries:
        cells = {
            f"{snap.scenario_id}:{snap.seed}": snap.model_dump()
            for snap in report.snapshots
            if snap.version == summary.version
        }
        if not cells:
            continue
        path = registry_dir / f"vocabulary_{summary.version}.json"
        path.write_text(
            json.dumps(
                {
                    "version": summary.version,
                    "semantic_labels": list(summary.semantic_labels),
                    "safety_states": list(summary.safety_states),
                    "recommendations": list(summary.recommendations),
                    "cells": cells,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


__all__ = [
    "ONTOLOGY_DRIFT_DISCLAIMER",
    "persist_version_vocabulary",
    "run_ontology_drift_detection",
]
