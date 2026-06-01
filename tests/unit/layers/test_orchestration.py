"""Unit tests for L6 Orchestration Layer."""

from __future__ import annotations

import pytest

from dualexis.orchestration import HIGH_RISK_SEVERITIES, SafetyOrchestrator


@pytest.mark.unit
def test_high_risk_severities_defined() -> None:
    assert "critical" in HIGH_RISK_SEVERITIES
    assert SafetyOrchestrator.__doc__ is not None
