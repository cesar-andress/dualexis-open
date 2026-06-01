"""Stability and dispersion statistics across seeds."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from dualexis.robustness.models import MetricDistribution, StabilityMetricKind


def jaccard_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def mean_pairwise_jaccard(signatures: Sequence[frozenset[str]]) -> float:
    """Mean Jaccard across all seed pairs."""
    if len(signatures) < 2:
        return 1.0
    scores: list[float] = []
    for index in range(len(signatures)):
        for other in range(index + 1, len(signatures)):
            scores.append(jaccard_similarity(signatures[index], signatures[other]))
    return statistics.mean(scores)


def per_seed_reference_stability(
    signatures_by_seed: dict[int, frozenset[str]],
    seeds: tuple[int, ...],
) -> list[float]:
    """Jaccard of each seed signature against the reference (first seed)."""
    if not seeds:
        return []
    reference = signatures_by_seed[seeds[0]]
    return [jaccard_similarity(signatures_by_seed[seed], reference) for seed in seeds]


def distribution_from_values(
    metric: StabilityMetricKind,
    values: Sequence[float],
) -> MetricDistribution:
    if not values:
        return MetricDistribution(
            metric=metric,
            mean=1.0,
            std=0.0,
            coefficient_of_variation=0.0,
            per_seed_values=(),
        )
    mean = statistics.mean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    if abs(mean) < 1e-9:
        cv = 0.0 if std < 1e-9 else float("inf")
    else:
        cv = std / mean
    if cv == float("inf"):
        cv = 0.0
    return MetricDistribution(
        metric=metric,
        mean=round(mean, 4),
        std=round(std, 4),
        coefficient_of_variation=round(cv, 4),
        per_seed_values=tuple(round(v, 4) for v in values),
    )


def compute_robustness_score(distributions: Sequence[MetricDistribution]) -> float:
    """
    Composite robustness score R in [0, 1].

    Higher when mean stability is high and coefficient of variation is low.
    """
    if not distributions:
        return 1.0
    means = [dist.mean for dist in distributions]
    cvs = [dist.coefficient_of_variation for dist in distributions]
    avg_stability = statistics.mean(means)
    avg_cv = statistics.mean(cvs)
    penalty = avg_cv / (1.0 + avg_cv)
    score = avg_stability * (1.0 - 0.5 * penalty)
    return round(max(0.0, min(1.0, score)), 4)


__all__ = [
    "compute_robustness_score",
    "distribution_from_values",
    "jaccard_similarity",
    "mean_pairwise_jaccard",
    "per_seed_reference_stability",
]
