"""Overlap ratios across world_dynamics, event_generator, and ground_truth_rules."""

from __future__ import annotations

from dualexis.leakage_audit.models import ComponentSpec, OverlapReport, ThresholdPredicate


def _threshold_key(pred: ThresholdPredicate, *, fuzzy_zone: bool = False) -> tuple[str, ...]:
    zone = pred.zone if not fuzzy_zone or pred.zone == "*" else pred.zone
    return (pred.metric, zone, pred.operator)


def _threshold_match(a: ThresholdPredicate, b: ThresholdPredicate, *, value_tol: float = 0.12) -> bool:
    if a.metric != b.metric:
        return False
    if a.operator != b.operator and not (
        a.operator in {"gt", "gte"} and b.operator in {"gt", "gte"}
    ):
        if a.operator in {"ramp", "decay"} or b.operator in {"ramp", "decay"}:
            return a.metric == b.metric
        return False
    zones_overlap = a.zone == b.zone or a.zone == "*" or b.zone == "*" or (
        a.zone == "exit-lobby" and b.zone == "exit-main"
    )
    if not zones_overlap:
        return False
    if a.operator in {"ramp", "decay"} or b.operator in {"ramp", "decay"}:
        return True
    return abs(a.value - b.value) <= value_tol


def _jaccard_shared_count(
    specs: tuple[ComponentSpec, ...],
    *,
    extractor,
) -> tuple[float, int]:
    sets = [extractor(spec) for spec in specs]
    if not sets:
        return 1.0, 0
    union: set = set()
    for item_set in sets:
        union |= item_set
    if not union:
        return 0.0, 0
    intersection = sets[0].copy()
    for item_set in sets[1:]:
        intersection &= item_set
    return len(intersection) / len(union), len(union)


def _variable_set(spec: ComponentSpec) -> set[str]:
    return set(spec.variables)


def _threshold_set(spec: ComponentSpec) -> set[tuple[str, str, str, int]]:
    """Bucket thresholds by metric, zone, operator, and deci-value bucket."""
    out: set[tuple[str, str, str, int]] = set()
    for pred in spec.thresholds:
        bucket = int(round(pred.value * 10))
        zone = pred.zone if pred.zone != "*" else "_any_"
        out.add((pred.metric, zone, pred.operator, bucket))
    return out


def _logic_set(spec: ComponentSpec) -> set[str]:
    return {f"{p.scenario_id}:{p.expression}" for p in spec.logic_predicates}


def pairwise_threshold_alignment(
    left: ComponentSpec,
    right: ComponentSpec,
    *,
    value_tol: float = 0.12,
) -> float:
    if not left.thresholds or not right.thresholds:
        return 0.0
    matched = 0
    for lp in left.thresholds:
        for rp in right.thresholds:
            if _threshold_match(lp, rp, value_tol=value_tol):
                matched += 1
                break
    return matched / max(len(left.thresholds), len(right.thresholds))


def compute_overlap_report(
    world: ComponentSpec,
    events: ComponentSpec,
    rules: ComponentSpec,
) -> OverlapReport:
    specs = (world, events, rules)
    var_ratio, var_union = _jaccard_shared_count(specs, extractor=_variable_set)
    thr_ratio, thr_union = _jaccard_shared_count(specs, extractor=_threshold_set)
    logic_ratio, logic_union = _jaccard_shared_count(specs, extractor=_logic_set)

    # Enrich threshold overlap with semantic pairwise alignment (generator vs rules)
    gen_rules_align = pairwise_threshold_alignment(events, rules)
    blended_threshold = 0.5 * thr_ratio + 0.5 * gen_rules_align

    return OverlapReport(
        shared_variables_ratio=round(var_ratio, 4),
        shared_threshold_ratio=round(blended_threshold, 4),
        shared_logic_ratio=round(logic_ratio, 4),
        variable_union_size=var_union,
        threshold_union_size=thr_union,
        logic_union_size=logic_union,
    )


__all__ = [
    "compute_overlap_report",
    "pairwise_threshold_alignment",
]
