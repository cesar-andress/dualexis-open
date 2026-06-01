"""Leakage score and independence estimates."""

from __future__ import annotations

from dualexis.leakage_audit.models import IndependenceEstimates, OverlapReport
from dualexis.leakage_audit.spec_extraction import independent_labeler_imports_event_generator

BENCHMARK_DISCLOSURE = (
    "This benchmark is procedurally independent but not distributionally independent."
)


def compute_leakage_score(overlap: OverlapReport) -> float:
    """Composite leakage score LS in [0, 1] (higher = more shared coupling)."""
    weights = (0.35, 0.45, 0.20)
    components = (
        overlap.shared_variables_ratio,
        overlap.shared_threshold_ratio,
        overlap.shared_logic_ratio,
    )
    score = sum(weight * value for weight, value in zip(weights, components, strict=True))
    return round(min(1.0, max(0.0, score)), 4)


def estimate_procedural_independence() -> float:
    """1.0 when labeler has no import coupling to event_generator."""
    return 0.0 if independent_labeler_imports_event_generator() else 1.0


def estimate_semantic_independence(overlap: OverlapReport) -> float:
    """1 - mean shared structural overlap (thresholds weighted higher)."""
    mean_shared = (
        0.25 * overlap.shared_variables_ratio
        + 0.55 * overlap.shared_threshold_ratio
        + 0.20 * overlap.shared_logic_ratio
    )
    return round(max(0.0, min(1.0, 1.0 - mean_shared)), 4)


def estimate_distributional_independence(
    *,
    ground_truth_stability: float,
    agreement_drift: float,
) -> float:
    """High when GT robust to threshold noise and agreement stable under perturbation."""
    # agreement_drift is 1 - agreement_change; stability from MC
    return round(
        max(0.0, min(1.0, 0.6 * ground_truth_stability + 0.4 * (1.0 - agreement_drift))),
        4,
    )


def build_independence_estimates(
    overlap: OverlapReport,
    *,
    ground_truth_stability: float,
    agreement_drift: float,
) -> IndependenceEstimates:
    return IndependenceEstimates(
        procedural_independence=estimate_procedural_independence(),
        semantic_independence=estimate_semantic_independence(overlap),
        distributional_independence=estimate_distributional_independence(
            ground_truth_stability=ground_truth_stability,
            agreement_drift=agreement_drift,
        ),
    )


__all__ = [
    "BENCHMARK_DISCLOSURE",
    "build_independence_estimates",
    "compute_leakage_score",
    "estimate_distributional_independence",
    "estimate_procedural_independence",
    "estimate_semantic_independence",
]
