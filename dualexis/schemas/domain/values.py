"""Strongly typed value objects for the DUALEXIS domain model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dualexis.schemas.common import NodeId, ZoneId
from dualexis.schemas.domain.validators import contains_forbidden_term, validate_metadata_dict


class ConfidenceScore(BaseModel):
    """Normalized confidence in ``[0.0, 1.0]`` with mandatory explainability."""

    model_config = ConfigDict(frozen=True)

    value: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(
        min_length=1,
        max_length=512,
        description="Human-readable explanation of how the score was derived",
    )


class LocationReference(BaseModel):
    """Anonymized spatial reference — zones and sites, never individual identities."""

    model_config = ConfigDict(frozen=True)

    zone_id: ZoneId
    zone_label: str = Field(min_length=1, max_length=128)
    site_id: str | None = Field(default=None, max_length=64)

    @field_validator("zone_label", "site_id")
    @classmethod
    def reject_identity_terms(cls, value: str | None) -> str | None:
        if value is None:
            return value
        matched = contains_forbidden_term(value)
        if matched is not None:
            msg = f"Location field contains forbidden term '{matched}'"
            raise ValueError(msg)
        return value


class EventSource(BaseModel):
    """Provenance of an event — edge node and modality, without personal data."""

    model_config = ConfigDict(frozen=True)

    node_id: NodeId
    modality: str = Field(min_length=1, max_length=32)
    pipeline_id: str | None = Field(default=None, max_length=64)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("modality", "pipeline_id")
    @classmethod
    def reject_identity_terms(cls, value: str | None) -> str | None:
        if value is None:
            return value
        matched = contains_forbidden_term(value)
        if matched is not None:
            msg = f"EventSource field contains forbidden term '{matched}'"
            raise ValueError(msg)
        return value

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        validate_metadata_dict(value)
        return value
