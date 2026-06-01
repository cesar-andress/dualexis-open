"""Unit tests for TSGG trust propagation."""

from __future__ import annotations

from pathlib import Path

from dualexis.tsgg.pipeline import run_tsgg_record
from dualexis.tsgg.trust_propagation import (
    TrustNodeKind,
    compose_trust,
    evidence_reliability,
    propagate_trust_batch,
    propagate_trust_for_record,
)
from dualexis.sssg.models import EvidenceKind, EvidenceRecord
from datetime import UTC, datetime


def test_compose_trust_bounds() -> None:
    assert compose_trust(0.9, 0.8) == 0.72


def test_evidence_reliability() -> None:
    ev = EvidenceRecord(
        evidence_id="e1",
        kind=EvidenceKind.ZONE_DENSITY,
        zone_id="z1",
        tick=1,
        timestamp=datetime.now(tz=UTC),
        metric_value=0.5,
        description="density spike",
    )
    assert 0.0 < evidence_reliability(ev) <= 1.0


def test_propagate_trust_for_record() -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    report = propagate_trust_for_record(record, benchmark_prior=0.9)
    assert report.nodes
    assert report.metrics.mean_node_trust > 0.0
    kinds = {node.kind for node in report.nodes}
    assert TrustNodeKind.EVIDENCE in kinds
    assert TrustNodeKind.CAUSAL_TRANSITION in kinds
    for trust in report.node_trust.values():
        assert 0.0 <= trust <= 1.0


def test_propagate_trust_batch(tmp_path: Path) -> None:
    records = [run_tsgg_record("exit_blockage", seed=1)]
    report = propagate_trust_batch(records)
    assert 0.0 <= report.metrics.trust_consistency <= 1.0
    assert 0.0 <= report.metrics.trust_decay <= 1.0
    assert report.path_trust
