"""Verify package imports and public API surface."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_dualexis_package_import() -> None:
    import dualexis
    from dualexis.core.version import get_version

    assert dualexis.__version__ == get_version()


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name",
    [
        "dualexis.core",
        "dualexis.schemas",
        "dualexis.fusion",
        "dualexis.privacy",
        "dualexis.orchestration",
        "dualexis.privacy_runtime",
        "dualexis.edge_perception",
        "dualexis.semantic_events",
        "dualexis.temporal_graph",
        "dualexis.local_reasoning",
        "dualexis.evaluation",
        "dualexis.simulation",
    ],
)
def test_core_submodules_import(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module.__doc__ is not None


@pytest.mark.unit
def test_schemas_public_exports() -> None:
    from dualexis.schemas import FusionInput, PrivacyPolicy, SafetyEvent

    assert SafetyEvent.__name__ == "SafetyEvent"
    assert PrivacyPolicy.__name__ == "PrivacyPolicy"
    assert FusionInput.__name__ == "FusionInput"


@pytest.mark.unit
def test_domain_public_exports() -> None:
    from dualexis.schemas.domain import (
        ConfidenceScore,
        EventType,
        NormalizedEvent,
        OrchestrationRecommendation,
    )

    assert ConfidenceScore.__name__ == "ConfidenceScore"
    assert EventType.__name__ == "EventType"
    assert NormalizedEvent.__name__ == "NormalizedEvent"
    assert OrchestrationRecommendation.__name__ == "OrchestrationRecommendation"
