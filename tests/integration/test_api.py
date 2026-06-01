"""Integration tests for the FastAPI application."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from dualexis.schemas.events import EventSeverity, SafetyEvent, SemanticDescriptor


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.integration
def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.integration
def test_publish_and_retrieve_event(client: TestClient) -> None:
    event = SafetyEvent(
        event_id="550e8400-e29b-41d4-a716-446655440000",
        node_id="edge-001",
        zone_id="hallway-a",
        severity=EventSeverity.MEDIUM,
        descriptors=(
            SemanticDescriptor(
                category="test",
                description="Integration test event",
                confidence=0.7,
            ),
        ),
    )
    response = client.post("/events", json={"event": event.model_dump(mode="json")})
    assert response.status_code == 201
    event_id = response.json()["event_id"]

    get_response = client.get(f"/events/{event_id}")
    assert get_response.status_code == 200
    assert get_response.json()["zone_id"] == "hallway-a"
