"""Procedural Agreement Rate (PAR) and related decoupled benchmark metrics."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.ground_truth import ScenarioGroundTruth


@dataclass(frozen=True)
class AgreementCounts:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def total(self) -> int:
        return self.true_positives + self.false_positives + self.false_negatives


@dataclass(frozen=True)
class ProceduralAgreementMetrics:
    par: float
    fpr: float
    fnr: float
    counts: AgreementCounts


@dataclass(frozen=True)
class BootstrapInterval:
    lower: float
    upper: float
    level: float = 0.95


def event_label_key(event: SemanticEvent) -> tuple[str, str]:
    return (event.zone_id, event.metadata.get("category", ""))


def ground_truth_label_key(label_zone_id: str, semantic_label: str) -> tuple[str, str]:
    return (label_zone_id, semantic_label)


def agreement_counts(
    predicted: tuple[SemanticEvent, ...],
    ground_truth: ScenarioGroundTruth,
) -> AgreementCounts:
    """Multiset TP/FP/FN on (zone_id, semantic_label) keys."""
    predicted_counts = Counter(event_label_key(event) for event in predicted)
    truth_counts = Counter(
        ground_truth_label_key(label.zone_id, label.semantic_label)
        for label in ground_truth.labels
    )
    keys = set(predicted_counts) | set(truth_counts)
    tp = fp = fn = 0
    for key in keys:
        predicted_n = predicted_counts.get(key, 0)
        truth_n = truth_counts.get(key, 0)
        tp += min(predicted_n, truth_n)
        if predicted_n > truth_n:
            fp += predicted_n - truth_n
        if truth_n > predicted_n:
            fn += truth_n - predicted_n
    return AgreementCounts(true_positives=tp, false_positives=fp, false_negatives=fn)


def procedural_agreement_metrics(
    predicted: tuple[SemanticEvent, ...],
    ground_truth: ScenarioGroundTruth,
) -> ProceduralAgreementMetrics:
    """Compute PAR, micro-FPR, and micro-FNR for one run."""
    counts = agreement_counts(predicted, ground_truth)
    total = counts.total
    if total == 0:
        return ProceduralAgreementMetrics(
            par=1.0,
            fpr=0.0,
            fnr=0.0,
            counts=counts,
        )
    par = counts.true_positives / total
    fpr = counts.false_positives / (counts.false_positives + counts.true_positives) if (
        counts.false_positives + counts.true_positives
    ) else 0.0
    fnr = counts.false_negatives / (counts.false_negatives + counts.true_positives) if (
        counts.false_negatives + counts.true_positives
    ) else 0.0
    return ProceduralAgreementMetrics(
        par=round(par, 4),
        fpr=round(fpr, 4),
        fnr=round(fnr, 4),
        counts=counts,
    )


def bootstrap_ci(
    values: list[float],
    *,
    level: float = 0.95,
    resamples: int = 10_000,
    seed: int = 42,
) -> BootstrapInterval:
    """Percentile bootstrap confidence interval for the mean."""
    if not values:
        return BootstrapInterval(lower=0.0, upper=0.0, level=level)
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    alpha = (1.0 - level) / 2.0
    lower_idx = int(alpha * resamples)
    upper_idx = int((1.0 - alpha) * resamples) - 1
    return BootstrapInterval(
        lower=round(means[lower_idx], 4),
        upper=round(means[upper_idx], 4),
        level=level,
    )


def aggregate_micro_rates(metrics: list[ProceduralAgreementMetrics]) -> ProceduralAgreementMetrics:
    """Micro-average PAR/FPR/FNR across runs."""
    tp = sum(m.counts.true_positives for m in metrics)
    fp = sum(m.counts.false_positives for m in metrics)
    fn = sum(m.counts.false_negatives for m in metrics)
    counts = AgreementCounts(true_positives=tp, false_positives=fp, false_negatives=fn)
    total = counts.total
    par = counts.true_positives / total if total else 1.0
    fpr = fp / (fp + tp) if (fp + tp) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0
    return ProceduralAgreementMetrics(
        par=round(par, 4),
        fpr=round(fpr, 4),
        fnr=round(fnr, 4),
        counts=counts,
    )


__all__ = [
    "AgreementCounts",
    "BootstrapInterval",
    "ProceduralAgreementMetrics",
    "aggregate_micro_rates",
    "agreement_counts",
    "bootstrap_ci",
    "event_label_key",
    "ground_truth_label_key",
    "procedural_agreement_metrics",
]
