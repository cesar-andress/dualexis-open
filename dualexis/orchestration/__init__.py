"""L6 Human-in-the-Loop Orchestration Layer — advisory pipeline (Framework Layer 6)."""

from dualexis.orchestration.interfaces import OrchestrationService
from dualexis.orchestration.models import (
    HIGH_RISK_SEVERITIES,
    ORCHESTRATION_LAYER,
    HumanReviewStatus,
    LayerMetadata,
    OrchestrationPhase,
    OrchestrationRecommendation,
    SeverityLevel,
)

__all__ = [
    "HIGH_RISK_SEVERITIES",
    "ORCHESTRATION_LAYER",
    "HumanReviewStatus",
    "LayerMetadata",
    "OrchestrationPhase",
    "OrchestrationRecommendation",
    "OrchestrationService",
    "SafetyOrchestrator",
    "SeverityLevel",
]


def __getattr__(name: str) -> object:
    if name == "SafetyOrchestrator":
        from dualexis.orchestration.service import SafetyOrchestrator

        return SafetyOrchestrator
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
