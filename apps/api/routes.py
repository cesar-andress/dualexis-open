"""FastAPI routes for safety event management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.services import InMemoryEventPublisher
from dualexis.schemas.domain import SafetyEvent

router = APIRouter(prefix="/events", tags=["events"])


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "dualexis-api"


class PublishEventRequest(BaseModel):
    event: SafetyEvent


class EventResponse(BaseModel):
    event_id: str
    status: str = "published"


def get_publisher() -> InMemoryEventPublisher:
    return _publisher


_publisher = InMemoryEventPublisher()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def publish_event(
    request: PublishEventRequest,
    publisher: Annotated[InMemoryEventPublisher, Depends(get_publisher)],
) -> EventResponse:
    event_id = await publisher.publish(request.event)
    return EventResponse(event_id=event_id)


@router.get("/{event_id}", response_model=SafetyEvent)
async def get_event(
    event_id: str,
    publisher: Annotated[InMemoryEventPublisher, Depends(get_publisher)],
) -> SafetyEvent:
    event = publisher.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.get("", response_model=list[SafetyEvent])
async def list_events(
    publisher: Annotated[InMemoryEventPublisher, Depends(get_publisher)],
) -> list[SafetyEvent]:
    return publisher.list_events()
