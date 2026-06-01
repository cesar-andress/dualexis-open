"""Adversarial privacy attack catalogue (beyond forbidden-key fuzz)."""

from __future__ import annotations

from dualexis.adversarial_privacy.models import AdversarialAttackKind, AdversarialPrivacyAttack


def default_adversarial_attacks() -> tuple[AdversarialPrivacyAttack, ...]:
    """Five attack classes for adversarial privacy stress testing."""
    return (
        AdversarialPrivacyAttack(
            attack_id="adv_indirect_identity",
            kind=AdversarialAttackKind.INDIRECT_IDENTITY_LEAKAGE,
            description=(
                "Indirect identity leakage via cohort tokens and institutional codes "
                "not on the literal forbidden-key list."
            ),
            payloads=(
                {
                    "zone_id": "cafeteria",
                    "homeroom_teacher_code": "T-442",
                    "guardian_contact_domain": "school.edu",
                    "learner_cohort_token": "7B-2026",
                },
            ),
        ),
        AdversarialPrivacyAttack(
            attack_id="adv_quasi_identifiers",
            kind=AdversarialAttackKind.QUASI_IDENTIFIER_COMBINATIONS,
            description=(
                "Quasi-identifier combination: fine-grained zone, tick, density, "
                "and device installation fingerprint."
            ),
            payloads=(
                {
                    "zone_id": "hall-a-west-wing",
                    "tick": 7,
                    "density": 0.412,
                    "activity_band": "high",
                    "device_installation_id": "edge-003-north",
                },
            ),
        ),
        AdversarialPrivacyAttack(
            attack_id="adv_temporal_linkage",
            kind=AdversarialAttackKind.TEMPORAL_LINKAGE,
            description=(
                "Temporal linkage attack: cross-tick session token ties observations "
                "across zones in metadata."
            ),
            payloads=(
                {
                    "zone_id": "cafeteria",
                    "tick": 3,
                    "session_token": "sess-9f2a",
                    "density": 0.38,
                },
                {
                    "zone_id": "hallway-b",
                    "tick": 4,
                    "session_token": "sess-9f2a",
                    "density": 0.41,
                },
                {
                    "zone_id": "exit-north",
                    "tick": 5,
                    "session_token": "sess-9f2a",
                    "density": 0.29,
                },
            ),
        ),
        AdversarialPrivacyAttack(
            attack_id="adv_repeated_correlation",
            kind=AdversarialAttackKind.REPEATED_EVENT_CORRELATION,
            description=(
                "Repeated rare-event correlation: identical rare signature across ticks "
                "enables occupant fingerprinting."
            ),
            payloads=(
                {
                    "zone_id": "cafeteria",
                    "tick": 2,
                    "rare_event_signature": "acoustic-spike-7k2",
                    "density": 0.44,
                },
                {
                    "zone_id": "cafeteria",
                    "tick": 5,
                    "rare_event_signature": "acoustic-spike-7k2",
                    "density": 0.46,
                },
                {
                    "zone_id": "cafeteria",
                    "tick": 8,
                    "rare_event_signature": "acoustic-spike-7k2",
                    "density": 0.43,
                },
            ),
        ),
        AdversarialPrivacyAttack(
            attack_id="adv_graph_reconstruction",
            kind=AdversarialAttackKind.GRAPH_RECONSTRUCTION,
            description=(
                "Graph reconstruction attack: explicit movement edges between zones "
                "in structured metadata."
            ),
            payloads=(
                {
                    "zone_id": "hallway-a",
                    "tick": 6,
                    "movement_graph_edge": "cafeteria->hallway-a->exit-north",
                    "prior_zone_id": "cafeteria",
                    "next_zone_id": "exit-north",
                    "traversal_sequence": "cafeteria,hallway-a,exit-north",
                },
            ),
        ),
    )


__all__ = ["default_adversarial_attacks"]
