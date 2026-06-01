"""Unit tests for TSGG unified framework."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.tsgg.metrics import compute_tsgg_unified_metrics
from dualexis.tsgg.models import TSGG_PIPELINE_CHAIN, TsggPipelineStage
from dualexis.tsgg.pipeline import run_tsgg_record


def test_pipeline_stages_order() -> None:
    assert tuple(TSGG_PIPELINE_CHAIN) == (
        TsggPipelineStage.EVIDENCE,
        TsggPipelineStage.SAFETY_STATE,
        TsggPipelineStage.CAUSAL_TRANSITION,
        TsggPipelineStage.RECOMMENDATION,
        TsggPipelineStage.GOVERNANCE_DECISION,
        TsggPipelineStage.AUDIT_TRACE,
    )


def test_run_tsgg_record_normal_flow() -> None:
    record = run_tsgg_record("normal_flow", seed=1)
    assert record.scenario_id == "normal_flow"
    assert record.seed == 1
    assert "evidence" in record.stage_counts
    assert record.causal_trace.scenario_id == "normal_flow"
    assert len(record.pipeline_output.recommendations) >= 0


def test_unified_metrics_use_formal_governance_audit() -> None:
    from dualexis.governance.formal_audit import run_formal_governance_audit
    from dualexis.leakage_audit.overlap import compute_overlap_report
    from dualexis.leakage_audit.scoring import (
        build_independence_estimates,
        compute_leakage_score,
    )
    from dualexis.leakage_audit.spec_extraction import extract_all_specs
    from dualexis.leakage_audit.models import LeakageAuditReport

    formal = run_formal_governance_audit(fast=True)
    record = run_tsgg_record("exit_blockage", seed=2)
    world, events, rules = extract_all_specs()
    overlap = compute_overlap_report(world, events, rules)
    independence = build_independence_estimates(overlap, ground_truth_stability=1.0, agreement_drift=0.0)
    leakage = LeakageAuditReport(
        leakage_score=compute_leakage_score(overlap),
        overlap=overlap,
        independence=independence,
        monte_carlo_iterations=1,
        ground_truth_stability_mean=1.0,
        event_stability_mean=1.0,
        agreement_drift_mean=0.0,
        benchmark_disclosure="test",
        dependency_graph_dot="digraph {}",
        per_scenario={},
    )
    metrics = compute_tsgg_unified_metrics(
        [record],
        leakage,
        formal_metrics=formal.metrics,
    )
    assert metrics.governance_compliance_score == formal.metrics.governance_compliance_score
    assert metrics.decision_traceability == formal.metrics.decision_traceability


def test_unified_metrics_bounds() -> None:
    record = run_tsgg_record("exit_blockage", seed=2)
    from dualexis.leakage_audit.overlap import compute_overlap_report
    from dualexis.leakage_audit.scoring import (
        build_independence_estimates,
        compute_leakage_score,
    )
    from dualexis.leakage_audit.spec_extraction import extract_all_specs
    from dualexis.leakage_audit.models import LeakageAuditReport

    world, events, rules = extract_all_specs()
    overlap = compute_overlap_report(world, events, rules)
    independence = build_independence_estimates(overlap, ground_truth_stability=1.0, agreement_drift=0.0)
    leakage = LeakageAuditReport(
        leakage_score=compute_leakage_score(overlap),
        overlap=overlap,
        independence=independence,
        monte_carlo_iterations=1,
        ground_truth_stability_mean=1.0,
        event_stability_mean=1.0,
        agreement_drift_mean=0.0,
        benchmark_disclosure="test",
        dependency_graph_dot="digraph {}",
        per_scenario={},
    )
    metrics = compute_tsgg_unified_metrics([record], leakage)
    assert 0.0 <= metrics.tsgg_trust_index <= 1.0
    assert 0.0 <= metrics.leakage_score <= 1.0


@pytest.mark.slow
def test_tsgg_framework_export(tmp_path: Path) -> None:
    from dualexis.tsgg.audit import run_tsgg_framework

    report = run_tsgg_framework(
        output_dir=tmp_path / "tsgg",
        paper_tables=tmp_path / "tables",
        paper_sections=tmp_path / "sections",
        paper_figures=tmp_path / "figures",
        scenarios=("normal_flow",),
        seeds=(1,),
        leakage_fast=True,
    )
    assert report.framework_json.is_file()
    assert report.section_tex.is_file()
    assert "TSGG" in report.section_tex.read_text(encoding="utf-8")
