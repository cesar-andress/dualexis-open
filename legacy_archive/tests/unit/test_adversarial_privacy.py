"""Tests for adversarial privacy stress framework."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.adversarial_privacy.attacks import default_adversarial_attacks
from dualexis.adversarial_privacy.export import export_adversarial_privacy_stress
from dualexis.adversarial_privacy.models import AdversarialAttackKind
from dualexis.adversarial_privacy.scoring import (
    privacy_resilience_index,
    reidentification_risk_from_payloads,
)
from dualexis.adversarial_privacy.stress import (
    run_adversarial_attack,
    run_adversarial_privacy_stress,
)


@pytest.mark.unit
def test_default_adversarial_attacks_count() -> None:
    attacks = default_adversarial_attacks()
    kinds = {attack.kind for attack in attacks}
    assert AdversarialAttackKind.INDIRECT_IDENTITY_LEAKAGE in kinds
    assert AdversarialAttackKind.GRAPH_RECONSTRUCTION in kinds
    assert len(attacks) == 5


@pytest.mark.unit
def test_reidentification_risk_bounded() -> None:
    attack = default_adversarial_attacks()[1]
    risk = reidentification_risk_from_payloads(attack.payloads)
    assert 0.0 <= risk <= 1.0


@pytest.mark.unit
def test_run_adversarial_attack_structure() -> None:
    result = run_adversarial_attack(default_adversarial_attacks()[0])
    assert result.attack_id
    assert 0.0 <= result.reidentification_risk <= 1.0
    assert 0.0 <= result.semantic_leakage_score <= 1.0


@pytest.mark.unit
def test_privacy_resilience_index_bounded() -> None:
    score = privacy_resilience_index(
        privacy_attack_success_rate=0.2,
        reidentification_risk=0.3,
        semantic_leakage_score=0.25,
        fuzz_pass_rate=1.0,
        l1_block_rate=0.4,
    )
    assert 0.0 <= score <= 1.0


@pytest.mark.unit
def test_run_adversarial_privacy_stress_report() -> None:
    report = run_adversarial_privacy_stress()
    assert report.metrics.attack_count == 5
    assert report.fuzz_case_count > 0
    assert 0.0 <= report.metrics.privacy_resilience_index <= 1.0


@pytest.mark.unit
def test_export_adversarial_privacy(tmp_path: Path) -> None:
    report = run_adversarial_privacy_stress()
    paths = export_adversarial_privacy_stress(
        report,
        tmp_path / "adv",
        paper_sections=tmp_path / "sections",
    )
    assert (tmp_path / "adv" / "adversarial_metrics.csv").is_file()
    assert (tmp_path / "adv" / "fuzz_baseline" / "results.csv").is_file()
    assert Path(paths["section_tex"]).is_file()
