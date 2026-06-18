"""Simulator event emission mode (decoupled vs shared-spec regression)."""

from __future__ import annotations

from enum import StrEnum


class EmissionMode(StrEnum):
    """How the simulator produces semantic events."""

    DECOUPLED = "decoupled"
    SHARED_SPEC = "shared_spec"


__all__ = ["EmissionMode"]
