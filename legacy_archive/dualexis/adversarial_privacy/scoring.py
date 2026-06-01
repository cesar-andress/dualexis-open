"""Risk and leakage scoring for adversarial privacy probes."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from dualexis.privacy_runtime.models import is_forbidden_field

# Fields that are allowed individually but risky in combination or as linkers.
QUASI_IDENTIFIER_KEYS: frozenset[str] = frozenset(
    {
        "zone_id",
        "tick",
        "timestamp",
        "density",
        "activity",
        "activity_band",
        "device_installation_id",
        "edge_node_id",
        "session_token",
        "correlation_id",
        "rare_event_signature",
    }
)

INDIRECT_IDENTITY_KEYS: frozenset[str] = frozenset(
    {
        "homeroom_teacher_code",
        "guardian_contact_domain",
        "learner_cohort_token",
        "class_roster_hash",
        "seat_assignment_code",
    }
)

LINKAGE_KEYS: frozenset[str] = frozenset(
    {
        "prior_zone_id",
        "next_zone_id",
        "traversal_sequence",
        "movement_graph_edge",
        "cross_zone_session",
    }
)


def _collect_keys(payload: Mapping[str, object], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in payload.items():
        full = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        keys.add(key.lower())
        if isinstance(value, dict):
            keys |= _collect_keys(value, full)
    return keys


def reidentification_risk_from_payloads(payloads: Sequence[Mapping[str, object]]) -> float:
    """
    Estimate re-identification risk from quasi-identifiers and indirect fields.

    Higher when more quasi-identifiers co-occur or indirect identity hints appear.
    """
    if not payloads:
        return 0.0
    scores: list[float] = []
    for payload in payloads:
        keys = _collect_keys(payload)
        quasi = len(keys & QUASI_IDENTIFIER_KEYS)
        indirect = len(keys & INDIRECT_IDENTITY_KEYS)
        linkage = len(keys & LINKAGE_KEYS)
        # Normalized combination risk (cap at 1.0)
        combo = min(1.0, (quasi / 5.0) * 0.5 + (indirect / 3.0) * 0.35 + (linkage / 3.0) * 0.15)
        scores.append(combo)
    return round(sum(scores) / len(scores), 4)


def semantic_leakage_score(
    payloads: Sequence[Mapping[str, object]],
    *,
    l1_blocked: bool,
) -> float:
    """
    Score residual semantic leakage if payloads were published.

    Zero when L1 blocks; otherwise proportional to linkable attributes retained.
    """
    if l1_blocked:
        return 0.0
    if not payloads:
        return 0.0
    leak_scores: list[float] = []
    for payload in payloads:
        keys = _collect_keys(payload)
        forbidden_present = any(is_forbidden_field(k.split(".")[-1]) for k in keys)
        if forbidden_present:
            leak_scores.append(1.0)
            continue
        linkable = len(keys & (QUASI_IDENTIFIER_KEYS | INDIRECT_IDENTITY_KEYS | LINKAGE_KEYS))
        leak_scores.append(min(1.0, linkable / 6.0))
    return round(sum(leak_scores) / len(leak_scores), 4)


def privacy_resilience_index(
    *,
    privacy_attack_success_rate: float,
    reidentification_risk: float,
    semantic_leakage_score: float,
    fuzz_pass_rate: float,
    l1_block_rate: float,
) -> float:
    """
    Composite privacy resilience in [0, 1] (higher is more resilient).

    Combines low attacker success, low re-id risk, low semantic leakage,
    high fuzz pass rate, and high L1 block rate on adversarial probes.
    """
    defense = (
        0.25 * (1.0 - privacy_attack_success_rate)
        + 0.20 * (1.0 - reidentification_risk)
        + 0.20 * (1.0 - semantic_leakage_score)
        + 0.20 * fuzz_pass_rate
        + 0.15 * l1_block_rate
    )
    return round(max(0.0, min(1.0, defense)), 4)


__all__ = [
    "semantic_leakage_score",
    "privacy_resilience_index",
    "reidentification_risk_from_payloads",
]
