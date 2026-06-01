"""Neo4j temporal safety graph backend — placeholder adapter."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from dualexis.schemas.domain import SafetyEvent
from dualexis.temporal_graph.interfaces import TemporalGraphBackend
from dualexis.temporal_graph.models import (
    Exit,
    GraphContext,
    GraphEdge,
    RecommendationNode,
    RiskState,
    Route,
    SemanticEventNode,
    Zone,
)


class Neo4jTemporalGraphBackend(TemporalGraphBackend):
    """Placeholder Neo4j adapter (not yet implemented).

    Defines the persistence contract for a future Cypher-backed implementation.
    All mutating methods raise ``NotImplementedError`` until a Neo4j driver is
    integrated behind the same ``TemporalGraphBackend`` interface.
    """

    def __init__(self, *, uri: str = "bolt://localhost:7687", database: str = "neo4j") -> None:
        self._uri = uri
        self._database = database

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def database(self) -> str:
        return self._database

    def add_zone(self, zone: Zone) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def add_exit(self, exit_node: Exit) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def add_route(self, route: Route) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def ingest_event(self, event_node: SemanticEventNode) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def add_edge(self, edge: GraphEdge) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def update_risk_state(self, state: RiskState) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def add_recommendation(self, recommendation: RecommendationNode) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def query_affected_routes(
        self,
        *,
        zone_id: str | None = None,
        exit_id: str | None = None,
    ) -> tuple[str, ...]:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def build_context(
        self,
        anchor_event_id: UUID,
        *,
        window: timedelta,
    ) -> GraphContext:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def store_legacy_event(self, event: SafetyEvent) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def get_legacy_context(
        self,
        event_id: UUID,
        *,
        window: timedelta,
    ) -> tuple[SafetyEvent, ...]:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def link_event_ids(self, source_id: UUID, target_id: UUID) -> None:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")

    def event_count(self) -> int:
        raise NotImplementedError("Neo4j backend is a placeholder in v0.1")


__all__ = ["Neo4jTemporalGraphBackend"]
