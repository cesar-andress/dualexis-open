"""Shared type definitions and identifiers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BeforeValidator, Field, PlainSerializer


def _parse_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


EventId = Annotated[
    UUID,
    BeforeValidator(_parse_uuid),
    PlainSerializer(lambda v: str(v), return_type=str, when_used="json"),
]

ZoneId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")]
NodeId = Annotated[str, Field(min_length=1, max_length=128)]


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(tz=UTC)
