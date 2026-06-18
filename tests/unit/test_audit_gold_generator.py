"""Unit tests for audit-task gold generation."""

from __future__ import annotations

import pytest

from dualexis.evaluation.audit_tasks.gold_generator import generate_task_gold
from dualexis.evaluation.audit_tasks.models import AuditTaskId
from dualexis.leakage_audit.audit import run_leakage_audit
from dualexis.tsgg.pipeline import run_tsgg_record


@pytest.fixture
def tmp_leakage(tmp_path):
    def _run(scenario: str):
        return run_leakage_audit(
            output_dir=tmp_path / "leakage",
            scenarios=(scenario,),
            fast=True,
        )

    return _run


@pytest.mark.unit
def test_generate_task_gold_has_all_tasks(tmp_leakage) -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    leakage = tmp_leakage("exit_blockage")
    gold = generate_task_gold(record, leakage_report=leakage)
    assert set(gold) == set(AuditTaskId)


@pytest.mark.unit
def test_a6_gold_contains_leakage_fields(tmp_leakage) -> None:
    record = run_tsgg_record("normal_flow", seed=1)
    leakage = tmp_leakage("normal_flow")
    gold = generate_task_gold(record, leakage_report=leakage)[AuditTaskId.A6_BENCHMARK_COUPLING]
    assert gold.applies
    assert gold.expected["leakage_score"] == leakage.leakage_score


@pytest.mark.unit
def test_a7_only_applies_to_evacuation_scenario() -> None:
    record = run_tsgg_record("evacuation_recommendation", seed=1)
    gold = generate_task_gold(record)[AuditTaskId.A7_EVACUATION_ZONE_COUNT]
    assert gold.applies
    assert isinstance(gold.expected, int)

    other = run_tsgg_record("normal_flow", seed=1)
    other_gold = generate_task_gold(other)[AuditTaskId.A7_EVACUATION_ZONE_COUNT]
    assert not other_gold.applies
