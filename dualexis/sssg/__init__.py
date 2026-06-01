"""Semantic Safety State Graph (SSSG) — evidence to state to transition to recommendation."""

from dualexis.sssg.metrics import StateGraphMetrics, compute_state_graph_metrics
from dualexis.sssg.models import (
    EvidenceRecord,
    SafetyState,
    SemanticSafetyStateGraph,
    StateTransition,
    StateTransitionTrace,
    TransitionEdgeKind,
)
from dualexis.sssg.service import SemanticSafetyStateGraphService
from dualexis.sssg.transitions import ALLOWED_TRANSITIONS, DOCUMENTED_TRANSITION_CHAINS

__all__ = [
    "ALLOWED_TRANSITIONS",
    "DOCUMENTED_TRANSITION_CHAINS",
    "EvidenceRecord",
    "SafetyState",
    "SemanticSafetyStateGraph",
    "SemanticSafetyStateGraphService",
    "StateGraphMetrics",
    "StateTransition",
    "StateTransitionTrace",
    "TransitionEdgeKind",
    "compute_state_graph_metrics",
]
