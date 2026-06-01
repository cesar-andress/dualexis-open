"""Infer typed causal factors and edges from SSSG evidence and transitions."""

from __future__ import annotations

from dualexis.sssg.models import EvidenceKind, EvidenceRecord, SafetyState, StateTransition
from dualexis.cssg.models import (
    CausalEdgeType,
    CausalFactor,
    CausalStateTransition,
    CausalTypedEdge,
)


def _confidence_from_evidence(evidence: tuple[EvidenceRecord, ...]) -> float:
    values = [e.metric_value for e in evidence if e.metric_value is not None]
    if not values:
        return 0.65
    return min(1.0, max(0.5, sum(values) / len(values)))


def _alternative_explanations(
    from_state: SafetyState,
    to_state: SafetyState,
    *,
    primary_factor: str,
) -> tuple[str, ...]:
    alts: list[str] = []
    if to_state == SafetyState.CROWDING_RISK:
        alts.append("Transient sensor spike rather than sustained crowding (monitor one tick).")
    if to_state == SafetyState.EXIT_IMPAIRMENT:
        alts.append("Scheduled maintenance affecting exit throughput, not blockage.")
    if to_state == SafetyState.EVACUATION_CANDIDATE:
        alts.append("Drill or planned assembly rather than emergency evacuation pattern.")
    if from_state != SafetyState.NORMAL:
        alts.append(f"Residual state from prior tick; primary driver disputed: {primary_factor}.")
    return tuple(alts[:2])


def infer_causal_factors(
    transition: StateTransition,
) -> tuple[CausalFactor, ...]:
    """Map evidence bundle to typed causal factors."""
    factors: list[CausalFactor] = []
    for record in transition.evidence:
        edge_type = _edge_type_for_evidence(record, transition.from_state, transition.to_state)
        factors.append(
            CausalFactor(
                factor_id=f"cf-{record.evidence_id}",
                edge_type=edge_type,
                description=record.description,
                evidence_id=record.evidence_id,
                weight=_factor_weight(record, edge_type),
            )
        )
    if not factors:
        factors.append(
            CausalFactor(
                factor_id=f"cf-{transition.zone_id}-{transition.tick}-baseline",
                edge_type=CausalEdgeType.CONTRIBUTES_TO,
                description="Baseline zone observation",
                evidence_id="baseline",
                weight=0.5,
            )
        )
    return tuple(factors)


def _edge_type_for_evidence(
    record: EvidenceRecord,
    from_state: SafetyState,
    to_state: SafetyState,
) -> CausalEdgeType:
    if to_state == SafetyState.NORMAL and from_state != SafetyState.NORMAL:
        return CausalEdgeType.MITIGATES
    if record.kind == EvidenceKind.EXIT_THROUGHPUT:
        if (record.metric_value or 1.0) < 0.55:
            return CausalEdgeType.TRIGGERS
        return CausalEdgeType.CONTRIBUTES_TO
    if record.kind == EvidenceKind.ZONE_DENSITY:
        val = record.metric_value or 0.0
        if val >= 0.52 and to_state == SafetyState.EVACUATION_CANDIDATE:
            return CausalEdgeType.TRIGGERS
        if val >= 0.38 and from_state == SafetyState.CROWDING_RISK:
            return CausalEdgeType.AGGRAVATES
        return CausalEdgeType.CONTRIBUTES_TO
    if record.kind == EvidenceKind.ZONE_AUDIO:
        if (record.metric_value or 0.0) >= 0.55:
            return CausalEdgeType.AGGRAVATES
        return CausalEdgeType.CONTRIBUTES_TO
    if record.kind == EvidenceKind.SEMANTIC_EVENT:
        desc = record.description.lower()
        if "evacuation" in desc or "stress" in desc:
            return CausalEdgeType.TRIGGERS
        if "conflict" in desc:
            return CausalEdgeType.AGGRAVATES
        return CausalEdgeType.CONTRIBUTES_TO
    return CausalEdgeType.CONTRIBUTES_TO


def _factor_weight(record: EvidenceRecord, edge_type: CausalEdgeType) -> float:
    base = record.metric_value if record.metric_value is not None else 0.6
    boost = {
        CausalEdgeType.TRIGGERS: 0.15,
        CausalEdgeType.AGGRAVATES: 0.1,
        CausalEdgeType.CONTRIBUTES_TO: 0.0,
        CausalEdgeType.MITIGATES: -0.05,
    }[edge_type]
    return min(1.0, max(0.2, base + boost))


def build_typed_causal_edges(
    transition: StateTransition,
    factors: tuple[CausalFactor, ...],
) -> tuple[CausalTypedEdge, ...]:
    edges: list[CausalTypedEdge] = []
    for factor in factors:
        edges.append(
            CausalTypedEdge(
                edge_type=factor.edge_type,
                from_state=transition.from_state,
                to_state=transition.to_state,
                factor_id=factor.factor_id,
                description=f"{factor.edge_type.value}: {factor.description}",
            )
        )
    return tuple(edges)


def enrich_transition(transition: StateTransition) -> CausalStateTransition:
    """Wrap an SSSG transition with CSSG causal attribution."""
    evidence = transition.evidence
    factors = infer_causal_factors(transition)
    typed_edges = build_typed_causal_edges(transition, factors)
    primary = factors[0].description if factors else "zone metrics"
    confidence = _confidence_from_evidence(evidence)
    return CausalStateTransition(
        transition_id=transition.transition_id,
        zone_id=transition.zone_id,
        tick=transition.tick,
        timestamp=transition.timestamp,
        from_state=transition.from_state,
        to_state=transition.to_state,
        explanation=transition.explanation,
        causal_factors=factors,
        confidence=round(confidence, 4),
        supporting_evidence=evidence,
        alternative_explanations=_alternative_explanations(
            transition.from_state,
            transition.to_state,
            primary_factor=primary,
        ),
        typed_causal_edges=typed_edges,
        sssg_edge_ids=transition.causal_edge_ids,
    )


__all__ = [
    "build_typed_causal_edges",
    "enrich_transition",
    "infer_causal_factors",
]
