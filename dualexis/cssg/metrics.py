"""CSSG evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

from dualexis.simulation.ground_truth import ScenarioGroundTruth
from dualexis.simulation.scenario import ScenarioId
from dualexis.sssg.metrics import compute_state_graph_metrics
from dualexis.sssg.models import EvidenceKind, SafetyState
from dualexis.cssg.models import CausalStateTransitionTrace
from dualexis.cssg.paths import causal_path_depth, find_root_causes


@dataclass(frozen=True)
class CausalGraphMetrics:
    """CSSG metric bundle."""

    transition_precision: float
    transition_recall: float
    state_consistency: float
    causal_trace_completeness: float
    causal_explanation_depth: float
    root_cause_precision: float
    causal_path_completeness: float
    explanation_stability_across_seeds: float


_EXPECTED_ROOT_KINDS: dict[str, frozenset[EvidenceKind]] = {
    ScenarioId.NORMAL_FLOW.value: frozenset({EvidenceKind.ZONE_ACTIVITY}),
    ScenarioId.CROWD_ACCELERATION.value: frozenset({EvidenceKind.ZONE_DENSITY}),
    ScenarioId.EXIT_BLOCKAGE.value: frozenset(
        {EvidenceKind.ZONE_DENSITY, EvidenceKind.EXIT_THROUGHPUT}
    ),
    ScenarioId.AUDIO_STRESS_SIGNAL.value: frozenset({EvidenceKind.ZONE_AUDIO}),
    ScenarioId.MULTIMODAL_CONFLICT.value: frozenset(
        {EvidenceKind.SEMANTIC_EVENT, EvidenceKind.ZONE_AUDIO}
    ),
    ScenarioId.EVACUATION_RECOMMENDATION.value: frozenset(
        {EvidenceKind.ZONE_DENSITY, EvidenceKind.SEMANTIC_EVENT}
    ),
}


def _evidence_kind_from_factor_description(description: str) -> EvidenceKind | None:
    lower = description.lower()
    if "density" in lower:
        return EvidenceKind.ZONE_DENSITY
    if "audio" in lower:
        return EvidenceKind.ZONE_AUDIO
    if "exit" in lower or "throughput" in lower:
        return EvidenceKind.EXIT_THROUGHPUT
    if "activity" in lower:
        return EvidenceKind.ZONE_ACTIVITY
    if "conflict" in lower or "evacuation" in lower or "stress" in lower:
        return EvidenceKind.SEMANTIC_EVENT
    return None


def compute_causal_graph_metrics(
    trace: CausalStateTransitionTrace,
    ground_truth: ScenarioGroundTruth,
) -> CausalGraphMetrics:
    """Compute CSSG metrics including causal depth and root-cause precision."""
    sssg_metrics = compute_state_graph_metrics(trace, ground_truth)

    depths: list[int] = []
    path_complete = 0
    root_hits = 0
    root_total = 0

    expected_kinds = _EXPECTED_ROOT_KINDS.get(trace.scenario_id, frozenset())

    zones = set(trace.zone_ids) or {t.zone_id for t in trace.causal_transitions}
    max_tick = max((t.tick for t in trace.causal_transitions), default=0)

    for zone_id in zones:
        depths.append(causal_path_depth(trace, zone_id, max_tick))
        roots = find_root_causes(trace, zone_id, max_tick)
        if roots:
            root_total += 1
            kinds = {
                k
                for f in roots
                for k in [_evidence_kind_from_factor_description(f.description)]
                if k is not None
            }
            if expected_kinds and kinds & expected_kinds:
                root_hits += 1
        path = trace.causal_transitions
        zone_path = [t for t in path if t.zone_id == zone_id]
        if zone_path and any(t.from_state == SafetyState.NORMAL for t in zone_path):
            path_complete += 1

    n_zones = len(zones) or 1
    causal_explanation_depth = sum(depths) / len(depths) if depths else 0.0
    root_cause_precision = root_hits / root_total if root_total else 1.0
    causal_path_completeness = path_complete / n_zones

    typed_complete = sum(
        1 for t in trace.causal_transitions if t.typed_causal_edges and t.causal_factors
    )
    n_trans = len(trace.causal_transitions) or 1
    causal_trace_completeness = typed_complete / n_trans

    return CausalGraphMetrics(
        transition_precision=sssg_metrics.transition_precision,
        transition_recall=sssg_metrics.transition_recall,
        state_consistency=sssg_metrics.state_consistency,
        causal_trace_completeness=causal_trace_completeness,
        causal_explanation_depth=round(causal_explanation_depth, 4),
        root_cause_precision=round(root_cause_precision, 4),
        causal_path_completeness=round(causal_path_completeness, 4),
        explanation_stability_across_seeds=1.0,
    )


def explanation_stability_across_seeds(
    traces: list[CausalStateTransitionTrace],
) -> float:
    """Jaccard stability of per-zone explanation chain signatures across seeds."""
    if len(traces) < 2:
        return 1.0

    def signature(trace: CausalStateTransitionTrace) -> frozenset[str]:
        parts: list[str] = []
        for transition in trace.causal_transitions:
            parts.append(
                f"{transition.zone_id}:{transition.from_state.value}->{transition.to_state.value}"
            )
        return frozenset(parts)

    base = signature(traces[0])
    scores: list[float] = []
    for other in traces[1:]:
        sig = signature(other)
        union = base | sig
        inter = base & sig
        scores.append(len(inter) / len(union) if union else 1.0)
        base = sig
    return round(sum(scores) / len(scores), 4)


def merge_with_stability(
    metrics: CausalGraphMetrics,
    traces: list[CausalStateTransitionTrace],
) -> CausalGraphMetrics:
    stability = explanation_stability_across_seeds(traces)
    return CausalGraphMetrics(
        transition_precision=metrics.transition_precision,
        transition_recall=metrics.transition_recall,
        state_consistency=metrics.state_consistency,
        causal_trace_completeness=metrics.causal_trace_completeness,
        causal_explanation_depth=metrics.causal_explanation_depth,
        root_cause_precision=metrics.root_cause_precision,
        causal_path_completeness=metrics.causal_path_completeness,
        explanation_stability_across_seeds=stability,
    )


__all__ = [
    "CausalGraphMetrics",
    "compute_causal_graph_metrics",
    "explanation_stability_across_seeds",
    "merge_with_stability",
]
