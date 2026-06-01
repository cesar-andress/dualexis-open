"""Ontology drift and stability metrics."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from dualexis.ontology_drift.models import (
    OntologySnapshot,
    ScenarioDriftMetrics,
    VersionOntologySummary,
)


def jaccard_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def mean_pairwise_jaccard(signatures: Sequence[frozenset[str]]) -> float:
    if len(signatures) < 2:
        return 1.0
    scores: list[float] = []
    for index in range(len(signatures)):
        for other in range(index + 1, len(signatures)):
            scores.append(jaccard_similarity(signatures[index], signatures[other]))
    return statistics.mean(scores)


def drift_from_stability(stability: float) -> float:
    """Convert stability in [0,1] to drift in [0,1]."""
    return round(max(0.0, min(1.0, 1.0 - stability)), 4)


def scenario_drift_metrics(
    snapshots: Sequence[OntologySnapshot],
    *,
    scenario_id: str,
    version: str,
) -> ScenarioDriftMetrics:
    """Compute per-scenario drift across seeds."""
    scenario_snaps = [s for s in snapshots if s.scenario_id == scenario_id and s.version == version]
    label_sigs = [frozenset(s.semantic_labels) for s in scenario_snaps]
    state_sigs = [frozenset(s.safety_states) for s in scenario_snaps]
    rec_sigs = [frozenset(s.recommendations) for s in scenario_snaps]

    label_stab = mean_pairwise_jaccard(label_sigs)
    state_stab = mean_pairwise_jaccard(state_sigs)
    rec_stab = mean_pairwise_jaccard(rec_sigs)

    semantic_drift = drift_from_stability(label_stab)
    state_drift = drift_from_stability(state_stab)
    recommendation_drift = drift_from_stability(rec_stab)
    ontology_stability = round(
        statistics.mean([label_stab, state_stab, rec_stab]),
        4,
    )

    return ScenarioDriftMetrics(
        scenario_id=scenario_id,
        version=version,
        semantic_drift=semantic_drift,
        safety_state_drift=state_drift,
        recommendation_drift=recommendation_drift,
        ontology_stability=ontology_stability,
    )


def summarize_version(snapshots: Sequence[OntologySnapshot], version: str) -> VersionOntologySummary:
    version_snaps = [s for s in snapshots if s.version == version]
    labels: set[str] = set()
    states: set[str] = set()
    recs: set[str] = set()
    for snap in version_snaps:
        labels.update(snap.semantic_labels)
        states.update(snap.safety_states)
        recs.update(snap.recommendations)
    return VersionOntologySummary(
        version=version,
        semantic_labels=tuple(sorted(labels)),
        safety_states=tuple(sorted(states)),
        recommendations=tuple(sorted(recs)),
        snapshot_count=len(version_snaps),
    )


def cross_version_vocab_drift(
    left: VersionOntologySummary,
    right: VersionOntologySummary,
) -> tuple[float, float, float]:
    """Drift between two version aggregates (labels, states, recommendations)."""
    label_drift = drift_from_stability(
        jaccard_similarity(frozenset(left.semantic_labels), frozenset(right.semantic_labels))
    )
    state_drift = drift_from_stability(
        jaccard_similarity(frozenset(left.safety_states), frozenset(right.safety_states))
    )
    rec_drift = drift_from_stability(
        jaccard_similarity(frozenset(left.recommendations), frozenset(right.recommendations))
    )
    return label_drift, state_drift, rec_drift


def aggregate_report_metrics(
    per_scenario: Sequence[ScenarioDriftMetrics],
) -> tuple[float, float, float]:
    if not per_scenario:
        return 1.0, 0.0, 0.0
    ontology_stability = statistics.mean(s.ontology_stability for s in per_scenario)
    semantic_drift = statistics.mean(s.semantic_drift for s in per_scenario)
    recommendation_drift = statistics.mean(s.recommendation_drift for s in per_scenario)
    return (
        round(ontology_stability, 4),
        round(semantic_drift, 4),
        round(recommendation_drift, 4),
    )


__all__ = [
    "aggregate_report_metrics",
    "cross_version_vocab_drift",
    "drift_from_stability",
    "jaccard_similarity",
    "mean_pairwise_jaccard",
    "scenario_drift_metrics",
    "summarize_version",
]
