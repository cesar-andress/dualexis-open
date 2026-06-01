"""Edge node telemetry counters."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class TelemetrySnapshot(BaseModel):
    """Point-in-time telemetry counters for an edge node."""

    model_config = ConfigDict(frozen=True)

    emissions_total: int = Field(default=0, ge=0)
    emissions_blocked: int = Field(default=0, ge=0)
    raw_media_blocked_total: int = Field(default=0, ge=0)
    last_emission_at: datetime | None = None


class EdgeTelemetry:
    """Mutable telemetry accumulator for edge event emissions."""

    def __init__(self) -> None:
        self._emissions_total = 0
        self._emissions_blocked = 0
        self._raw_media_blocked_total = 0
        self._last_emission_at: datetime | None = None

    def record_emission(self) -> None:
        self._emissions_total += 1
        self._last_emission_at = datetime.now(tz=UTC)

    def record_blocked(self, *, raw_media: bool = False) -> None:
        self._emissions_blocked += 1
        if raw_media:
            self._raw_media_blocked_total += 1

    def snapshot(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            emissions_total=self._emissions_total,
            emissions_blocked=self._emissions_blocked,
            raw_media_blocked_total=self._raw_media_blocked_total,
            last_emission_at=self._last_emission_at,
        )


__all__ = ["EdgeTelemetry", "TelemetrySnapshot"]
