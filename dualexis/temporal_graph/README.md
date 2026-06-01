# L4: Temporal Safety Graph Layer

Zone-scoped temporal context for situational awareness.

## Purpose

Maintain an in-memory **Temporal Safety Graph** of `SafetyEvent` nodes and typed relationships to support operator comprehension and grounded local reasoning (L5).

## Inputs

- `SafetyEvent` — privacy-validated semantic events from L3
- Optional `GraphEdge` relationship requests between event IDs
- Context query: anchor event ID + time window

## Outputs

- Stored event nodes (zone-local, non-identifying)
- `get_context()` — ordered related events within a sliding window
- Graph size metrics for evaluation

## Privacy constraints

- Nodes wrap events only — no person entities or media attachments
- No cross-session identity linking
- Graph retention bounded by configured max node count and policy tiers

## Future implementation plan

- Persistent graph backend with metadata-only storage (Neo4j / in-memory TTL)
- SPARQL-style queries for evaluation grounding metrics
- Propagation rules for multi-zone confined-space topologies
- Simulation-driven benchmark for graph update latency (L4 metrics)

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `TemporalGraphService` ABC |
| `models.py` | `GraphEdge`, `EventGraphNode`, context window defaults |
| `service.py` | `InMemoryTemporalGraphService` placeholder store |

## Usage

```python
from dualexis.temporal_graph import InMemoryTemporalGraphService

graph = InMemoryTemporalGraphService()
graph.add_event(event)
context = graph.get_context(event.event_id)
```
