"""In-memory temporal safety graph backend."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from dualexis.schemas.domain import SafetyEvent
from dualexis.temporal_graph.interfaces import TemporalGraphBackend
from dualexis.temporal_graph.models import (
    Exit,
    GraphContext,
    GraphEdge,
    GraphEntityKind,
    GraphRelation,
    RecommendationNode,
    RiskState,
    Route,
    SemanticEventNode,
    Zone,
)

_BLOCKAGE_EVENT_TYPES = frozenset(
    {
        "exit_blockage",
        "environmental_sensor",
        "route_unavailable",
    }
)
_CONFLICT_EVENT_TYPES = frozenset(
    {
        "multimodal_conflict",
        "multimodal_fusion",
        "unknown",
    }
)
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class InMemoryTemporalGraphBackend(TemporalGraphBackend):
    """Reference in-memory store for the temporal safety graph."""

    def __init__(self, *, max_events: int = 1000) -> None:
        self._max_events = max_events
        self._zones: dict[str, Zone] = {}
        self._exits: dict[str, Exit] = {}
        self._routes: dict[str, Route] = {}
        self._events: dict[UUID, SemanticEventNode] = {}
        self._risk_states: dict[str, RiskState] = {}
        self._recommendations: dict[UUID, RecommendationNode] = {}
        self._edges: list[GraphEdge] = []
        self._legacy_events: dict[UUID, SafetyEvent] = {}
        self._related_event_ids: dict[UUID, set[UUID]] = {}

    def add_zone(self, zone: Zone) -> None:
        self._zones[zone.zone_id] = zone
        for adjacent_id in zone.adjacent_zone_ids:
            if adjacent_id in self._zones:
                self._ensure_edge(
                    GraphRelation.CONNECTS_TO,
                    source_id=zone.zone_id,
                    source_kind=GraphEntityKind.ZONE,
                    target_id=adjacent_id,
                    target_kind=GraphEntityKind.ZONE,
                )

    def add_exit(self, exit_node: Exit) -> None:
        self._exits[exit_node.exit_id] = exit_node
        if exit_node.zone_id in self._zones:
            self._ensure_edge(
                GraphRelation.CONNECTS_TO,
                source_id=exit_node.exit_id,
                source_kind=GraphEntityKind.EXIT,
                target_id=exit_node.zone_id,
                target_kind=GraphEntityKind.ZONE,
            )

    def add_route(self, route: Route) -> None:
        self._routes[route.route_id] = route
        for zone_id in route.zone_ids:
            if zone_id in self._zones:
                self._ensure_edge(
                    GraphRelation.CONNECTS_TO,
                    source_id=route.route_id,
                    source_kind=GraphEntityKind.ROUTE,
                    target_id=zone_id,
                    target_kind=GraphEntityKind.ZONE,
                )
        for exit_id in route.exit_ids:
            if exit_id in self._exits:
                self._ensure_edge(
                    GraphRelation.CONNECTS_TO,
                    source_id=route.route_id,
                    source_kind=GraphEntityKind.ROUTE,
                    target_id=exit_id,
                    target_kind=GraphEntityKind.EXIT,
                )

    def ingest_event(self, event_node: SemanticEventNode) -> None:
        self._events[event_node.node_id] = event_node
        self._evict_if_needed()

        if event_node.zone_id in self._zones:
            self._ensure_edge(
                GraphRelation.OCCURRED_IN,
                source_id=str(event_node.node_id),
                source_kind=GraphEntityKind.SEMANTIC_EVENT,
                target_id=event_node.zone_id,
                target_kind=GraphEntityKind.ZONE,
            )

        self._apply_blockage_relations(event_node)
        self._apply_conflict_relations(event_node)
        self._apply_severity_relations(event_node)

    def add_edge(self, edge: GraphEdge) -> None:
        self._edges.append(edge)

    def update_risk_state(self, state: RiskState) -> None:
        previous = self._risk_states.get(state.zone_id)
        self._risk_states[state.zone_id] = state
        if previous is not None and state.risk_score > previous.risk_score:
            self._ensure_edge(
                GraphRelation.ESCALATES,
                source_id=state.zone_id,
                source_kind=GraphEntityKind.RISK_STATE,
                target_id=state.zone_id,
                target_kind=GraphEntityKind.RISK_STATE,
                metadata={"previous_score": f"{previous.risk_score:.4f}"},
            )
        elif previous is not None and state.risk_score < previous.risk_score:
            self._ensure_edge(
                GraphRelation.DEESCALATES,
                source_id=state.zone_id,
                source_kind=GraphEntityKind.RISK_STATE,
                target_id=state.zone_id,
                target_kind=GraphEntityKind.RISK_STATE,
                metadata={"previous_score": f"{previous.risk_score:.4f}"},
            )

    def add_recommendation(self, recommendation: RecommendationNode) -> None:
        self._recommendations[recommendation.recommendation_id] = recommendation
        self._ensure_edge(
            GraphRelation.RECOMMENDS,
            source_id=str(recommendation.recommendation_id),
            source_kind=GraphEntityKind.RECOMMENDATION,
            target_id=recommendation.zone_id,
            target_kind=GraphEntityKind.ZONE,
        )

    def query_affected_routes(
        self,
        *,
        zone_id: str | None = None,
        exit_id: str | None = None,
    ) -> tuple[str, ...]:
        affected: set[str] = set()
        for edge in self._edges:
            if edge.relation not in {GraphRelation.BLOCKS, GraphRelation.AFFECTS}:
                continue
            if edge.target_kind != GraphEntityKind.ROUTE:
                continue
            if not self._edge_matches_route_query(edge, zone_id=zone_id, exit_id=exit_id):
                continue
            affected.add(edge.target_id)
        return tuple(sorted(affected))

    def _edge_matches_route_query(
        self,
        edge: GraphEdge,
        *,
        zone_id: str | None,
        exit_id: str | None,
    ) -> bool:
        if (
            exit_id is not None
            and edge.source_id != exit_id
            and not (
                edge.relation == GraphRelation.AFFECTS
                and edge.source_kind == GraphEntityKind.SEMANTIC_EVENT
            )
        ):
            return False
        if zone_id is None:
            return True
        route = self._routes.get(edge.target_id)
        if route is not None and zone_id in route.zone_ids:
            return True
        if edge.source_id == zone_id:
            return True
        exit_node = self._exits.get(edge.source_id)
        return exit_node is not None and exit_node.zone_id == zone_id

    def build_context(
        self,
        anchor_event_id: UUID,
        *,
        window: timedelta,
    ) -> GraphContext:
        anchor = self._events.get(anchor_event_id)
        if anchor is None:
            return GraphContext(anchor_event_id=anchor_event_id)

        cutoff = anchor.timestamp - window
        zone_ids: set[str] = {anchor.zone_id}
        event_nodes = [anchor]

        for event in self._events.values():
            if event.node_id == anchor_event_id:
                continue
            if event.zone_id == anchor.zone_id and event.timestamp >= cutoff:
                event_nodes.append(event)
                zone_ids.add(event.zone_id)

        for zone_id in list(zone_ids):
            if zone_id in self._zones:
                zone_ids.update(self._zones[zone_id].adjacent_zone_ids)

        relevant_edges: list[GraphEdge] = []
        node_id_strs = {str(event.node_id) for event in event_nodes}
        entity_ids: set[str] = set(node_id_strs) | zone_ids
        entity_ids.update(
            exit_node.exit_id for exit_node in self._exits.values() if exit_node.zone_id in zone_ids
        )
        entity_ids.update(
            route.route_id for route in self._routes.values() if set(route.zone_ids) & zone_ids
        )

        for edge in self._edges:
            if edge.source_id in entity_ids or edge.target_id in entity_ids:
                relevant_edges.append(edge)

        affected = self.query_affected_routes(zone_id=anchor.zone_id)

        return GraphContext(
            anchor_event_id=anchor_event_id,
            zones=tuple(self._zones[z] for z in sorted(zone_ids) if z in self._zones),
            exits=tuple(
                exit_node for exit_node in self._exits.values() if exit_node.zone_id in zone_ids
            ),
            routes=tuple(
                route
                for route in self._routes.values()
                if set(route.zone_ids) & zone_ids or route.route_id in affected
            ),
            events=tuple(sorted(event_nodes, key=lambda node: node.timestamp)),
            risk_states=tuple(
                self._risk_states[z] for z in sorted(zone_ids) if z in self._risk_states
            ),
            recommendations=tuple(
                recommendation
                for recommendation in self._recommendations.values()
                if recommendation.zone_id in zone_ids
            ),
            edges=tuple(relevant_edges),
            affected_route_ids=affected,
        )

    def store_legacy_event(self, event: SafetyEvent) -> None:
        event_uuid = (
            event.event_id if isinstance(event.event_id, UUID) else UUID(str(event.event_id))
        )
        self._legacy_events[event_uuid] = event

    def get_legacy_context(
        self,
        event_id: UUID,
        *,
        window: timedelta,
    ) -> tuple[SafetyEvent, ...]:
        anchor = self._legacy_events.get(event_id)
        if anchor is None:
            return ()

        cutoff = anchor.timestamp - window
        context: list[SafetyEvent] = []
        for other in self._legacy_events.values():
            if other.event_id == event_id:
                continue
            if other.zone_id == anchor.zone_id and other.timestamp >= cutoff:
                context.append(other)

        for related_id in self._related_event_ids.get(event_id, set()):
            related = self._legacy_events.get(related_id)
            if related is not None and related not in context:
                context.append(related)

        return tuple(sorted(context, key=lambda event: event.timestamp))

    def link_event_ids(self, source_id: UUID, target_id: UUID) -> None:
        if source_id not in self._related_event_ids:
            self._related_event_ids[source_id] = set()
        if target_id not in self._related_event_ids:
            self._related_event_ids[target_id] = set()
        self._related_event_ids[source_id].add(target_id)
        self._related_event_ids[target_id].add(source_id)

        self._ensure_edge(
            GraphRelation.SUPPORTS,
            source_id=str(source_id),
            source_kind=GraphEntityKind.SEMANTIC_EVENT,
            target_id=str(target_id),
            target_kind=GraphEntityKind.SEMANTIC_EVENT,
        )

    def event_count(self) -> int:
        return len(self._events)

    def _apply_blockage_relations(self, event_node: SemanticEventNode) -> None:
        category = event_node.metadata.get("category", "")
        is_blockage = event_node.event_type in _BLOCKAGE_EVENT_TYPES or category in {
            "exit_blocked",
            "exit_blockage",
            "obstruction",
        }
        if not is_blockage:
            return

        zone_exits = [
            exit_node
            for exit_node in self._exits.values()
            if exit_node.zone_id == event_node.zone_id
        ]
        for exit_node in zone_exits:
            for route in self._routes.values():
                if exit_node.exit_id not in route.exit_ids:
                    continue
                self._ensure_edge(
                    GraphRelation.BLOCKS,
                    source_id=exit_node.exit_id,
                    source_kind=GraphEntityKind.EXIT,
                    target_id=route.route_id,
                    target_kind=GraphEntityKind.ROUTE,
                )
                self._ensure_edge(
                    GraphRelation.AFFECTS,
                    source_id=str(event_node.node_id),
                    source_kind=GraphEntityKind.SEMANTIC_EVENT,
                    target_id=route.route_id,
                    target_kind=GraphEntityKind.ROUTE,
                )

    def _apply_conflict_relations(self, event_node: SemanticEventNode) -> None:
        category = event_node.metadata.get("category", "")
        is_conflict = (
            event_node.event_type in _CONFLICT_EVENT_TYPES and "conflict" in category.lower()
        ) or event_node.event_type == "multimodal_conflict"

        if not is_conflict:
            return

        for other in self._events.values():
            if other.node_id == event_node.node_id:
                continue
            if other.zone_id != event_node.zone_id:
                continue
            if other.event_type == event_node.event_type:
                continue
            self._ensure_edge(
                GraphRelation.CONTRADICTS,
                source_id=str(event_node.node_id),
                source_kind=GraphEntityKind.SEMANTIC_EVENT,
                target_id=str(other.node_id),
                target_kind=GraphEntityKind.SEMANTIC_EVENT,
            )

    def _apply_severity_relations(self, event_node: SemanticEventNode) -> None:
        prior_events = [
            event
            for event in self._events.values()
            if event.node_id != event_node.node_id and event.zone_id == event_node.zone_id
        ]
        if not prior_events:
            return

        latest = max(prior_events, key=lambda event: event.timestamp)
        current_rank = _SEVERITY_ORDER.get(event_node.severity.lower(), 0)
        prior_rank = _SEVERITY_ORDER.get(latest.severity.lower(), 0)
        if current_rank > prior_rank:
            relation = GraphRelation.ESCALATES
        elif current_rank < prior_rank:
            relation = GraphRelation.DEESCALATES
        else:
            relation = GraphRelation.SUPPORTS

        self._ensure_edge(
            relation,
            source_id=str(event_node.node_id),
            source_kind=GraphEntityKind.SEMANTIC_EVENT,
            target_id=str(latest.node_id),
            target_kind=GraphEntityKind.SEMANTIC_EVENT,
        )

    def _ensure_edge(
        self,
        relation: GraphRelation,
        *,
        source_id: str,
        source_kind: GraphEntityKind,
        target_id: str,
        target_kind: GraphEntityKind,
        weight: float = 1.0,
        metadata: dict[str, str] | None = None,
    ) -> None:
        for edge in self._edges:
            if (
                edge.relation == relation
                and edge.source_id == source_id
                and edge.target_id == target_id
            ):
                return
        self._edges.append(
            GraphEdge(
                edge_id=uuid4(),
                relation=relation,
                source_id=source_id,
                source_kind=source_kind,
                target_id=target_id,
                target_kind=target_kind,
                weight=weight,
                created_at=datetime.now(tz=UTC),
                metadata=metadata or {},
            )
        )

    def _evict_if_needed(self) -> None:
        if len(self._events) <= self._max_events:
            return
        oldest_id = min(self._events, key=lambda key: self._events[key].timestamp)
        del self._events[oldest_id]


__all__ = ["InMemoryTemporalGraphBackend"]
