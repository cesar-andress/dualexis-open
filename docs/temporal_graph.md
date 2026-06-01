# Temporal Safety Graph (L4)

The Temporal Safety Graph Layer (L4) provides **structured situational context** for local reasoning and orchestration. Nodes represent zones, exits, routes, semantic events, risk states, and recommendations — never identities or biometric attributes.

Canonical implementation: `dualexis/temporal_graph/`.

## Architecture

Publication diagram: [temporal safety graph](diagrams/temporal_safety_graph.mmd) · [Markdown embed](diagrams/embeds.md#3-temporal-safety-graph) · rendered [SVG](diagrams/temporal_safety_graph.svg)

```
SemanticEvent / SafetyEvent
        │
        ▼
InMemoryTemporalGraphService
        │
        ▼
InMemoryTemporalGraphBackend  (Neo4jTemporalGraphBackend — placeholder)
        │
        ▼
GraphContext → Local Reasoning (L5)
```

## Graph Entities

| Entity | Description |
| ------ | ----------- |
| `Zone` | Spatial zone vertex |
| `Exit` | Egress point linked to a zone |
| `Route` | Circulation/evacuation path through zones and exits |
| `SemanticEventNode` | Zone-scoped semantic event |
| `RiskState` | Aggregate zone risk score |
| `RecommendationNode` | Human-in-the-loop recommendation |

## Graph Relations

| Relation | Meaning |
| -------- | ------- |
| `OCCURRED_IN` | Event observed in zone |
| `CONNECTS_TO` | Zone/route/exit topology |
| `BLOCKS` | Exit blocks route |
| `AFFECTS` | Event affects route availability |
| `ESCALATES` | Risk or severity increased |
| `DEESCALATES` | Risk or severity decreased |
| `SUPPORTS` | Corroborating events |
| `CONTRADICTS` | Conflicting semantic hypotheses |
| `RECOMMENDS` | Recommendation targets zone |

## Service API

```python
from dualexis.temporal_graph import (
    Exit,
    InMemoryTemporalGraphService,
    Route,
    Zone,
)

graph = InMemoryTemporalGraphService()
graph.add_zone(Zone(zone_id="exit-c", label="Exit C"))
graph.add_exit(Exit(exit_id="exit-c-main", zone_id="exit-c", label="Exit C Main"))
graph.add_route(
    Route(
        route_id="evac-south",
        label="South Route",
        zone_ids=("hall-a", "exit-c"),
        exit_ids=("exit-c-main",),
    )
)

node = graph.ingest_semantic_event(event)
affected = graph.query_affected_routes(zone_id="exit-c")
context = graph.get_reasoning_context(event.event_id)
payload = context.to_json_dict()
```

## Backward Compatibility

Legacy methods remain supported for pipeline and orchestrator integration:

- `add_event(SafetyEvent)`
- `get_context(event_id)` → `tuple[SafetyEvent, ...]`
- `link_events(source_id, target_id)`
- `size()`

## Backends

| Backend | Status |
| ------- | ------ |
| `InMemoryTemporalGraphBackend` | ✅ Reference implementation |
| `Neo4jTemporalGraphBackend` | Placeholder interface (raises `NotImplementedError`) |

## Privacy Constraints

- No person, face, or track nodes
- Graph context validated against forbidden identity/biometric fields
- Queries scoped by `zone_id` and sliding time window (`DEFAULT_CONTEXT_WINDOW = 300s`)

## Related Documentation

- [Framework](framework.md)
- [Pipeline](pipeline.md)
- LaTeX: `paper/sections/temporal_graph.tex`
