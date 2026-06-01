"""L3 Semantic Event Layer — typed safety events (Framework Layer 3)."""

# ruff: noqa: I001 — taxonomy must load before models (import-cycle guard)
from dualexis.schemas.domain import FusionResult, SafetyEvent
from dualexis.semantic_events.interfaces import SemanticEventService

# isort: off — taxonomy before models to avoid circular package initialization
from dualexis.semantic_events.taxonomy import (
    EVENT_TAXONOMY,
    EventCategory,
    InputModality,
    TaxonomyEventDefinition,
    TaxonomyEventType,
    all_event_types,
    events_by_category,
    get_event_definition,
    validate_taxonomy_registry,
)
from dualexis.semantic_events.models import (
    SEMANTIC_EVENTS_LAYER,
    EventSource,
    EventType,
    LayerMetadata,
    SemanticEvent,
)

# isort: on
from dualexis.semantic_events.service import (
    DefaultSemanticEventService,
    PlaceholderSemanticEventService,
)

__all__ = [
    "EVENT_TAXONOMY",
    "SEMANTIC_EVENTS_LAYER",
    "DefaultSemanticEventService",
    "EventCategory",
    "EventSource",
    "EventType",
    "FusionResult",
    "InputModality",
    "LayerMetadata",
    "PlaceholderSemanticEventService",
    "SafetyEvent",
    "SemanticEvent",
    "SemanticEventService",
    "TaxonomyEventDefinition",
    "TaxonomyEventType",
    "all_event_types",
    "events_by_category",
    "get_event_definition",
    "validate_taxonomy_registry",
]
