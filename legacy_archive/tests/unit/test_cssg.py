"""Tests for Causal Safety State Graph (CSSG)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.cssg.causal_factors import enrich_transition
from dualexis.cssg.chains import build_explanation_chain, canonical_escalation_chain_text
from dualexis.cssg.models import CausalEdgeType
from dualexis.cssg.paths import find_root_causes
from dualexis.cssg.runner import build_cssg_trace_from_scenario, evaluate_cssg_trace
from dualexis.cssg.service import CausalSafetyStateGraphService
from dualexis.experiments.cssg_battery import run_cssg_battery
from dualexis.sssg.runner import build_sssg_trace_from_scenario


@pytest.mark.unit
def test_causal_transition_has_required_fields() -> None:
    sssg_trace = build_sssg_trace_from_scenario("exit_blockage", seed=1)
    assert sssg_trace.transitions
    causal = enrich_transition(sssg_trace.transitions[0])
    assert causal.causal_factors
    assert 0.0 <= causal.confidence <= 1.0
    assert causal.supporting_evidence
    assert causal.alternative_explanations is not None
    assert causal.typed_causal_edges
    assert any(e.edge_type == CausalEdgeType.CONTRIBUTES_TO for e in causal.typed_causal_edges)


@pytest.mark.unit
def test_find_root_causes_exit_blockage() -> None:
    trace = build_cssg_trace_from_scenario("exit_blockage", seed=1)
    assert trace.causal_transitions
    zone = trace.causal_transitions[0].zone_id
    tick = max(t.tick for t in trace.causal_transitions)
    roots = find_root_causes(trace, zone, tick)
    assert roots


@pytest.mark.unit
def test_explanation_chain_contains_states() -> None:
    trace = build_cssg_trace_from_scenario("evacuation_recommendation", seed=1)
    chain = build_explanation_chain(trace, trace.zone_ids[0] if trace.zone_ids else "cafeteria")
    assert "NORMAL" in chain or "CROWDING RISK" in chain
    canonical = canonical_escalation_chain_text()
    assert "EVACUATION CANDIDATE" in canonical


@pytest.mark.unit
def test_cssg_metrics_bounded() -> None:
    _, metrics = evaluate_cssg_trace("exit_blockage", seed=1)
    assert 0.0 <= metrics.root_cause_precision <= 1.0
    assert 0.0 <= metrics.causal_path_completeness <= 1.0
    assert metrics.causal_explanation_depth >= 0.0


@pytest.mark.unit
def test_cssg_service_find_root_causes() -> None:
    trace = build_cssg_trace_from_scenario("crowd_acceleration", seed=2)
    service = CausalSafetyStateGraphService(scenario_id="crowd_acceleration", seed=2)
    service._graph.causal_transitions.extend(trace.causal_transitions)
    roots = service.find_root_causes("cafeteria", tick=5)
    assert isinstance(roots, tuple)


@pytest.mark.unit
def test_cssg_battery_export(tmp_path: Path) -> None:
    report = run_cssg_battery(
        output_dir=tmp_path / "cssg",
        paper_tables=tmp_path / "tables",
        paper_figures=tmp_path / "figures",
        paper_sections=tmp_path / "sections",
        scenarios=("exit_blockage",),
        seeds=(1, 2),
    )
    assert report.metrics_tex.is_file()
    assert report.section_tex.is_file()
    assert "exit_blockage" in report.metrics_csv.read_text(encoding="utf-8")
