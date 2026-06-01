"""Tests for counterfactual safety reasoning."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.counterfactual.interventions import (
    STANDARD_INTERVENTIONS,
    apply_intervention,
)
from dualexis.counterfactual.metrics import (
    counterfactual_consistency_for_recommendation,
    counterfactual_explanation_coverage,
)
from dualexis.counterfactual.models import CounterfactualInterventionKind
from dualexis.counterfactual.reasoning import (
    build_counterfactual_recommendation,
    simulate_counterfactual_scenario,
)
from dualexis.counterfactual.evaluation import collect_counterfactual_recommendations
from dualexis.experiments.counterfactual_battery import run_counterfactual_battery
from dualexis.sssg.models import EvidenceKind, EvidenceRecord
from dualexis.sssg.runner import build_sssg_trace_from_scenario
from datetime import UTC, datetime


def _sample_evidence(zone_id: str = "cafeteria") -> tuple[EvidenceRecord, ...]:
    now = datetime.now(tz=UTC)
    return (
        EvidenceRecord(
            evidence_id="ev-1",
            kind=EvidenceKind.ZONE_DENSITY,
            zone_id=zone_id,
            tick=2,
            timestamp=now,
            metric_value=0.45,
            description="Zone density 0.45",
        ),
        EvidenceRecord(
            evidence_id="ev-2",
            kind=EvidenceKind.EXIT_THROUGHPUT,
            zone_id=zone_id,
            tick=2,
            timestamp=now,
            metric_value=0.40,
            description="Exit throughput 0.40",
        ),
    )


@pytest.mark.unit
def test_apply_density_intervention() -> None:
    evidence = _sample_evidence()
    perturbed = apply_intervention(
        evidence,
        CounterfactualInterventionKind.DENSITY_BELOW_THRESHOLD,
        zone_id="cafeteria",
    )
    density = next(e for e in perturbed if e.kind == EvidenceKind.ZONE_DENSITY)
    assert density.metric_value == 0.35


@pytest.mark.unit
def test_simulate_counterfactual_scenario_question() -> None:
    cf = simulate_counterfactual_scenario(
        _sample_evidence(),
        intervention=CounterfactualInterventionKind.DENSITY_BELOW_THRESHOLD,
        zone_id="cafeteria",
        scenario_id="exit_blockage",
        spec_id="cf-test-0",
    )
    assert cf.question.startswith("What would have happened if")
    assert "below threshold" in cf.hypothesis


@pytest.mark.unit
def test_build_counterfactual_recommendation_three_interventions() -> None:
    trace = build_sssg_trace_from_scenario("exit_blockage", seed=1)
    from dualexis.counterfactual.reasoning import synthesize_recommendation_from_trace

    rec = synthesize_recommendation_from_trace(trace, zone_id="cafeteria")
    assert rec is not None
    cf_rec = build_counterfactual_recommendation(
        rec, trace, scenario_id="exit_blockage", seed=1
    )
    assert cf_rec is not None
    assert len(cf_rec.counterfactuals) == len(STANDARD_INTERVENTIONS)
    assert counterfactual_explanation_coverage(cf_rec) == 1.0
    assert 0.0 <= counterfactual_consistency_for_recommendation(cf_rec) <= 1.0


@pytest.mark.unit
def test_collect_counterfactual_recommendations_exit_blockage() -> None:
    recs = collect_counterfactual_recommendations("exit_blockage", seed=1)
    assert recs
    assert all(len(r.counterfactuals) >= 3 for r in recs)


@pytest.mark.unit
def test_counterfactual_battery_export(tmp_path: Path) -> None:
    report = run_counterfactual_battery(
        output_dir=tmp_path / "cf",
        paper_sections=tmp_path / "sections",
        scenarios=("exit_blockage",),
        seeds=(1, 2),
    )
    assert (tmp_path / "cf" / "counterfactual_metrics.csv").is_file()
    assert (tmp_path / "cf" / "counterfactual_report.json").is_file()
    assert report.section_tex.is_file()
    assert report.report.recommendation_count > 0
