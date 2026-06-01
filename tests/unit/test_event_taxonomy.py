"""Unit tests for the formal DUALEXIS event taxonomy."""

from __future__ import annotations

import pytest

from dualexis.schemas.domain.validators import contains_forbidden_term
from dualexis.semantic_events.taxonomy import (
    EVENT_TAXONOMY,
    EventCategory,
    TaxonomyEventType,
    all_event_types,
    events_by_category,
    get_event_definition,
    validate_taxonomy_registry,
)


@pytest.mark.unit
class TestTaxonomyRegistry:
    def test_registry_is_complete(self) -> None:
        validate_taxonomy_registry()
        assert len(EVENT_TAXONOMY) == len(TaxonomyEventType)
        assert len(all_event_types()) == 22

    def test_every_category_has_events(self) -> None:
        for category in EventCategory:
            assert events_by_category(category), f"{category} has no events"

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_get_event_definition(self, event_type: TaxonomyEventType) -> None:
        definition = get_event_definition(event_type)
        assert definition.event_type == event_type


@pytest.mark.unit
class TestTaxonomyValidationRules:
    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_every_event_type_has_description(self, event_type: TaxonomyEventType) -> None:
        definition = get_event_definition(event_type)
        assert definition.description.strip()

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_every_event_type_has_at_least_one_modality(
        self,
        event_type: TaxonomyEventType,
    ) -> None:
        definition = get_event_definition(event_type)
        assert len(definition.input_modalities) >= 1

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_no_event_type_requires_identity(self, event_type: TaxonomyEventType) -> None:
        definition = get_event_definition(event_type)
        assert definition.requires_identity is False

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_no_event_type_requires_biometric(self, event_type: TaxonomyEventType) -> None:
        definition = get_event_definition(event_type)
        assert definition.requires_biometric is False

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_descriptions_exclude_forbidden_terms(
        self,
        event_type: TaxonomyEventType,
    ) -> None:
        definition = get_event_definition(event_type)
        assert contains_forbidden_term(definition.description) is None

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_example_payloads_are_non_empty(self, event_type: TaxonomyEventType) -> None:
        definition = get_event_definition(event_type)
        assert definition.example_synthetic_payload
        assert "zone_id" in definition.example_synthetic_payload

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_confidence_range_is_valid(self, event_type: TaxonomyEventType) -> None:
        definition = get_event_definition(event_type)
        low, high = definition.expected_confidence_range
        assert 0.0 <= low <= high <= 1.0

    @pytest.mark.parametrize("event_type", list(TaxonomyEventType))
    def test_severity_mapping_covers_unit_interval(
        self,
        event_type: TaxonomyEventType,
    ) -> None:
        definition = get_event_definition(event_type)
        assert definition.severity_mapping.severity_for_confidence(0.0)
        assert definition.severity_mapping.severity_for_confidence(1.0)
