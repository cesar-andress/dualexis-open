"""Temporal safety graph domain models (L4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dualexis.schemas.domain.validators import validate_metadata_dict
from dualexis.semantic_events.models import SemanticEvent


class GraphRelation(StrEnum):
    """Typed relationships in the temporal safety graph."""

    OCCURRED_IN = "occurred_in"
    CONNECTS_TO = "connects_to"
    BLOCKS = "blocks"
    AFFECTS = "affects"
    ESCALATES = "escalates"
    DEESCALATES = "deescalates"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    RECOMMENDS = "recommends"


class GraphEntityKind(StrEnum):
    """Node kinds stored in the temporal safety graph."""

    ZONE = "zone"
    EXIT = "exit"
    ROUTE = "route"
    SEMANTIC_EVENT = "semantic_event"
    RISK_STATE = "risk_state"
    RECOMMENDATION = "recommendation"


class Zone(BaseModel):
    """Spatial zone vertex — aggregate semantics only, no identity."""

    model_config = ConfigDict(frozen=True)

    zone_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    adjacent_zone_ids: tuple[str, ...] = Field(default_factory=tuple)


class Exit(BaseModel):
    """Egress point connected to a zone."""

    model_config = ConfigDict(frozen=True)

    exit_id: str = Field(min_length=1, max_length=64)
    zone_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)


class Route(BaseModel):
    """Circulation or evacuation route through zones and exits."""

    model_config = ConfigDict(frozen=True)

    route_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    zone_ids: tuple[str, ...] = Field(default_factory=tuple)
    exit_ids: tuple[str, ...] = Field(default_factory=tuple)


class SemanticEventNode(BaseModel):
    """Graph node representing a zone-scoped semantic event."""

    model_config = ConfigDict(frozen=True)

    node_id: UUID
    zone_id: str = Field(min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    severity: str = Field(min_length=1, max_length=32)
    explanation: str = Field(min_length=1, max_length=2048)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        validate_metadata_dict(value)
        return value

    @classmethod
    def from_semantic_event(cls, event: SemanticEvent) -> SemanticEventNode:
        return cls(
            node_id=event.event_id,
            zone_id=event.zone_id,
            event_type=event.event_type.value,
            timestamp=event.timestamp,
            confidence=event.confidence,
            severity=event.severity.value,
            explanation=event.explanation,
            metadata=dict(event.metadata),
        )


class RiskState(BaseModel):
    """Aggregate risk posture for a zone at a point in time."""

    model_config = ConfigDict(frozen=True)

    zone_id: str = Field(min_length=1, max_length=64)
    risk_score: float = Field(ge=0.0, le=1.0)
    updated_at: datetime
    label: str = Field(default="normal", min_length=1, max_length=64)


class RecommendationNode(BaseModel):
    """Human-in-the-loop recommendation attached to the graph."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: UUID
    zone_id: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=128)
    severity: str = Field(min_length=1, max_length=32)
    created_at: datetime
    rationale: str = Field(min_length=1, max_length=2048)


class GraphEdge(BaseModel):
    """Directed typed edge between graph entities."""

    model_config = ConfigDict(frozen=True)

    edge_id: UUID = Field(default_factory=uuid4)
    relation: GraphRelation
    source_id: str = Field(min_length=1, max_length=128)
    source_kind: GraphEntityKind
    target_id: str = Field(min_length=1, max_length=128)
    target_kind: GraphEntityKind
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, str] = Field(default_factory=dict)


class GraphContext(BaseModel):
    """Structured, privacy-preserving graph snapshot for local reasoning."""

    model_config = ConfigDict(frozen=True)

    anchor_event_id: UUID
    zones: tuple[Zone, ...] = Field(default_factory=tuple)
    exits: tuple[Exit, ...] = Field(default_factory=tuple)
    routes: tuple[Route, ...] = Field(default_factory=tuple)
    events: tuple[SemanticEventNode, ...] = Field(default_factory=tuple)
    risk_states: tuple[RiskState, ...] = Field(default_factory=tuple)
    recommendations: tuple[RecommendationNode, ...] = Field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = Field(default_factory=tuple)
    affected_route_ids: tuple[str, ...] = Field(default_factory=tuple)

    def to_json_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary representation."""
        return self.model_dump(mode="json")


# Legacy aliases retained for framework domain tests and migration.
class TemporalEdgeKind(StrEnum):
    """Relationship type between events in the temporal graph (legacy)."""

    TEMPORAL = "temporal"
    ADJACENCY = "adjacency"
    FUSION = "fusion"
    RISK_PROPAGATION = "risk_propagation"


class TemporalGraphEdge(BaseModel):
    """Directed edge linking two semantic events within a bounded context window."""

    model_config = ConfigDict(frozen=True)

    edge_id: UUID
    source_event_id: UUID
    target_event_id: UUID
    kind: TemporalEdgeKind
    weight: float = Field(ge=0.0, le=1.0)
    created_at: datetime


class TemporalGraphNode(BaseModel):
    """Graph node wrapping a semantic event with optional local risk score."""

    model_config = ConfigDict(frozen=True)

    node_id: UUID
    event: SemanticEvent
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)


DEFAULT_CONTEXT_WINDOW_SECONDS: int = 300
DEFAULT_CONTEXT_WINDOW = timedelta(seconds=DEFAULT_CONTEXT_WINDOW_SECONDS)

GraphEdgeType = GraphRelation
GraphEdgeTypeLegacy = TemporalEdgeKind


@dataclass(frozen=True, slots=True)
class LayerMetadata:
    """Static metadata for the Temporal Safety Graph Layer."""

    layer_id: str = "L4"
    name: str = "Temporal Safety Graph Layer"
    processes_events_only: bool = True


TEMPORAL_GRAPH_LAYER = LayerMetadata()


__all__ = [
    "DEFAULT_CONTEXT_WINDOW",
    "DEFAULT_CONTEXT_WINDOW_SECONDS",
    "TEMPORAL_GRAPH_LAYER",
    "Exit",
    "GraphContext",
    "GraphEdge",
    "GraphEdgeType",
    "GraphEdgeTypeLegacy",
    "GraphEntityKind",
    "GraphRelation",
    "LayerMetadata",
    "RecommendationNode",
    "RiskState",
    "Route",
    "SemanticEvent",
    "SemanticEventNode",
    "TemporalEdgeKind",
    "TemporalGraphEdge",
    "TemporalGraphNode",
    "Zone",
]
