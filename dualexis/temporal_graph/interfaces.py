"""L4 Temporal Safety Graph Layer — service and backend interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from uuid import UUID

from dualexis.schemas.domain import SafetyEvent
from dualexis.semantic_events.models import SemanticEvent
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


class TemporalGraphBackend(ABC):
    """Persistence adapter for the temporal safety graph."""

    @abstractmethod
    def add_zone(self, zone: Zone) -> None:
        """Insert or replace a zone vertex."""

    @abstractmethod
    def add_exit(self, exit_node: Exit) -> None:
        """Insert or replace an exit vertex."""

    @abstractmethod
    def add_route(self, route: Route) -> None:
        """Insert or replace a route vertex."""

    @abstractmethod
    def ingest_event(self, event_node: SemanticEventNode) -> None:
        """Insert a semantic event node and derive graph relations."""

    @abstractmethod
    def add_edge(self, edge: GraphEdge) -> None:
        """Insert a typed graph edge."""

    @abstractmethod
    def update_risk_state(self, state: RiskState) -> None:
        """Upsert zone risk state."""

    @abstractmethod
    def add_recommendation(self, recommendation: RecommendationNode) -> None:
        """Insert a recommendation node."""

    @abstractmethod
    def query_affected_routes(
        self,
        *,
        zone_id: str | None = None,
        exit_id: str | None = None,
    ) -> tuple[str, ...]:
        """Return route identifiers affected by blockage or risk."""

    @abstractmethod
    def build_context(
        self,
        anchor_event_id: UUID,
        *,
        window: timedelta,
    ) -> GraphContext:
        """Build a structured graph snapshot for local reasoning."""

    @abstractmethod
    def store_legacy_event(self, event: SafetyEvent) -> None:
        """Store a legacy SafetyEvent for backward-compatible context queries."""

    @abstractmethod
    def get_legacy_context(
        self,
        event_id: UUID,
        *,
        window: timedelta,
    ) -> tuple[SafetyEvent, ...]:
        """Return legacy SafetyEvent context for an anchor event."""

    @abstractmethod
    def link_event_ids(self, source_id: UUID, target_id: UUID) -> None:
        """Create bidirectional SUPPORTS links between event nodes."""

    @abstractmethod
    def event_count(self) -> int:
        """Return the number of ingested semantic event nodes."""


class TemporalGraphService(ABC):
    """Maintains zone-scoped temporal graph context for reasoning."""

    @abstractmethod
    def add_zone(self, zone: Zone) -> None:
        """Insert a zone vertex."""

    @abstractmethod
    def add_exit(self, exit_node: Exit) -> None:
        """Insert an exit vertex."""

    @abstractmethod
    def add_route(self, route: Route) -> None:
        """Insert a route vertex."""

    @abstractmethod
    def ingest_semantic_event(self, event: SemanticEvent) -> SemanticEventNode:
        """Ingest a domain semantic event into the graph."""

    @abstractmethod
    def update_risk_state(self, state: RiskState) -> RiskState:
        """Update aggregate zone risk."""

    @abstractmethod
    def query_affected_routes(
        self,
        *,
        zone_id: str | None = None,
        exit_id: str | None = None,
    ) -> tuple[str, ...]:
        """Return routes affected by blockages or elevated risk."""

    @abstractmethod
    def get_reasoning_context(
        self,
        event_id: UUID,
        *,
        window: timedelta | None = None,
    ) -> GraphContext:
        """Produce structured graph context for local reasoning."""

    @abstractmethod
    def add_event(self, event: SafetyEvent) -> None:
        """Insert a legacy SafetyEvent into the graph."""

    @abstractmethod
    def link_events(self, source_id: UUID, target_id: UUID) -> None:
        """Create bidirectional related-event links."""

    @abstractmethod
    def get_context(
        self,
        event_id: UUID,
        *,
        window: timedelta | None = None,
    ) -> tuple[SafetyEvent, ...]:
        """Retrieve zone-local temporal context for an anchor event."""

    @abstractmethod
    def size(self) -> int:
        """Return current semantic event node count."""
