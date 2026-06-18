"""Unit tests for audit-comparison baseline exporters."""

from __future__ import annotations

import pytest

from dualexis.evaluation.exporters import ExportFormat, build_audit_trace_exports
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
def test_build_audit_trace_exports_all_formats(tmp_leakage) -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    leakage = tmp_leakage("exit_blockage")
    exports = build_audit_trace_exports(record, leakage_report=leakage)
    assert exports.scenario_id == "exit_blockage"
    assert exports.seed == 1
    for export_format in ExportFormat:
        payload = exports.payload(export_format)
        assert payload["scenario_id"] == "exit_blockage"
        assert payload["seed"] == 1


@pytest.mark.unit
def test_flat_json_is_chronological_without_graph_schema() -> None:
    record = run_tsgg_record("multimodal_conflict", seed=2)
    exports = build_audit_trace_exports(record)
    records = exports.flat_json["records"]
    timestamps = [row["timestamp"] for row in records]
    assert timestamps == sorted(timestamps)
    assert "edges" not in exports.flat_json
    assert all("record_type" in row for row in records)


@pytest.mark.unit
def test_prov_export_has_derivation_edges() -> None:
    record = run_tsgg_record("crowd_acceleration", seed=1)
    prov = build_audit_trace_exports(record).prov
    assert prov.get("wasDerivedFrom")
    assert prov.get("entity")
    assert prov.get("activity")
    assert prov.get("prefix")


@pytest.mark.unit
def test_xes_export_has_trace_events() -> None:
    record = run_tsgg_record("normal_flow", seed=1)
    xes = build_audit_trace_exports(record).xes
    traces = xes["log"]["traces"]
    assert len(traces) == 1
    assert traces[0]["events"]
