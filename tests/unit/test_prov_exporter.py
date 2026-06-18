"""PROV-JSON export validation via ProvPy round-trip."""

from __future__ import annotations

import pytest

from dualexis.evaluation.exporters.prov_exporter import (
    export_prov_document,
    roundtrip_prov_document,
)
from dualexis.tsgg.pipeline import run_tsgg_record


@pytest.mark.unit
def test_prov_export_roundtrip_deserializes() -> None:
    record = run_tsgg_record("exit_blockage", seed=1)
    payload = export_prov_document(record)
    assert payload["format"] == "prov_json"
    assert payload["entity"]
    doc = roundtrip_prov_document(payload)
    assert doc is not None


@pytest.mark.unit
def test_prov_export_has_standard_prefix_and_derivations() -> None:
    record = run_tsgg_record("crowd_acceleration", seed=1)
    payload = export_prov_document(record)
    assert "prefix" in payload
    assert payload.get("wasDerivedFrom")
