"""Run adversarial privacy stress (fuzz battery + linkage attacks)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from dualexis.adversarial_privacy.attacks import default_adversarial_attacks
from dualexis.adversarial_privacy.models import (
    AdversarialAttackResult,
    AdversarialPrivacyAttack,
    AdversarialPrivacyMetrics,
    AdversarialPrivacyReport,
)
from dualexis.adversarial_privacy.scoring import (
    privacy_resilience_index,
    reidentification_risk_from_payloads,
    semantic_leakage_score,
)
from dualexis.core.exceptions import PrivacyViolationError
from dualexis.evaluation.privacy_fuzz_battery import (
    PRIVACY_FUZZ_DISCLAIMER,
    run_privacy_fuzz_battery,
)
from dualexis.privacy_runtime import DEFAULT_PRIVACY_POLICY, validate_payload_privacy

ADVERSARIAL_PRIVACY_DISCLAIMER = (
    "Adversarial privacy stress framework (synthetic). Evaluates privacy beyond "
    "forbidden-key validation: linkage, quasi-identifiers, and semantic residual risk. "
    "Not a certification audit or legal DPIA."
)


def _probe_payloads(payloads: Sequence[dict[str, object]]) -> tuple[bool, str]:
    """Return (l1_blocked, violation_type) for a payload sequence."""
    for payload in payloads:
        try:
            validate_payload_privacy(payload, DEFAULT_PRIVACY_POLICY)
        except PrivacyViolationError as exc:
            return True, str(exc)
    return False, ""


def run_adversarial_attack(attack: AdversarialPrivacyAttack) -> AdversarialAttackResult:
    """Execute one adversarial attack against L1 and score residual risk."""
    l1_blocked, violation_type = _probe_payloads(attack.payloads)
    reid_risk = reidentification_risk_from_payloads(attack.payloads)
    leakage = semantic_leakage_score(attack.payloads, l1_blocked=l1_blocked)

    # Attack succeeds for the adversary if linkable semantics could publish (not blocked).
    attack_succeeded = not l1_blocked and (reid_risk >= 0.35 or leakage >= 0.35)

    notes = (
        "Blocked by L1 fail-closed validator."
        if l1_blocked
        else "Passed forbidden-key gate; residual linkage risk scored."
    )

    return AdversarialAttackResult(
        attack_id=attack.attack_id,
        kind=attack.kind,
        description=attack.description,
        l1_blocked=l1_blocked,
        attack_succeeded=attack_succeeded,
        reidentification_risk=reid_risk,
        semantic_leakage_score=leakage,
        violation_type=violation_type,
        notes=notes,
    )


def run_adversarial_attacks(
    attacks: Sequence[AdversarialPrivacyAttack] | None = None,
) -> tuple[AdversarialAttackResult, ...]:
    selected = list(attacks or default_adversarial_attacks())
    return tuple(run_adversarial_attack(attack) for attack in selected)


def compute_adversarial_metrics(
    results: Sequence[AdversarialAttackResult],
    *,
    fuzz_pass_rate: float,
) -> AdversarialPrivacyMetrics:
    if not results:
        return AdversarialPrivacyMetrics(
            reidentification_risk=0.0,
            privacy_attack_success_rate=0.0,
            semantic_leakage_score=0.0,
            privacy_resilience_index=1.0,
            fuzz_pass_rate=fuzz_pass_rate,
            attack_count=0,
            l1_block_rate=1.0,
        )

    reid = sum(r.reidentification_risk for r in results) / len(results)
    leakage = sum(r.semantic_leakage_score for r in results) / len(results)
    success = sum(1 for r in results if r.attack_succeeded) / len(results)
    block_rate = sum(1 for r in results if r.l1_blocked) / len(results)

    resilience = privacy_resilience_index(
        privacy_attack_success_rate=success,
        reidentification_risk=reid,
        semantic_leakage_score=leakage,
        fuzz_pass_rate=fuzz_pass_rate,
        l1_block_rate=block_rate,
    )

    return AdversarialPrivacyMetrics(
        reidentification_risk=round(reid, 4),
        privacy_attack_success_rate=round(success, 4),
        semantic_leakage_score=round(leakage, 4),
        privacy_resilience_index=resilience,
        fuzz_pass_rate=round(fuzz_pass_rate, 4),
        attack_count=len(results),
        l1_block_rate=round(block_rate, 4),
    )


def run_adversarial_privacy_stress(
    *,
    include_fuzz: bool = True,
) -> AdversarialPrivacyReport:
    """Run legacy fuzz battery plus adversarial linkage attacks."""
    fuzz_results = run_privacy_fuzz_battery() if include_fuzz else ()
    fuzz_pass = sum(1 for row in fuzz_results if row.rejected == row.expect_rejection)
    fuzz_pass_rate = fuzz_pass / len(fuzz_results) if fuzz_results else 1.0

    adversarial_results = run_adversarial_attacks()
    metrics = compute_adversarial_metrics(adversarial_results, fuzz_pass_rate=fuzz_pass_rate)

    return AdversarialPrivacyReport(
        generated_at=datetime.now(tz=UTC),
        disclaimer=f"{PRIVACY_FUZZ_DISCLAIMER} {ADVERSARIAL_PRIVACY_DISCLAIMER}",
        adversarial_results=adversarial_results,
        metrics=metrics,
        fuzz_case_count=len(fuzz_results),
        fuzz_pass_count=fuzz_pass,
    )


__all__ = [
    "ADVERSARIAL_PRIVACY_DISCLAIMER",
    "compute_adversarial_metrics",
    "run_adversarial_attack",
    "run_adversarial_attacks",
    "run_adversarial_privacy_stress",
]
