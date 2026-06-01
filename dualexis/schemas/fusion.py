"""Multimodal fusion input schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from dualexis.schemas.common import NodeId, ZoneId
from dualexis.schemas.perception import PerceptionSignal


class ModalityWeight(BaseModel):
    """Weight assigned to a modality during fusion."""

    model_config = ConfigDict(frozen=True, strict=True)

    modality: str
    weight: float = Field(ge=0.0, le=1.0)


class FusionInput(BaseModel):
    """Input bundle for multimodal fusion within a time window."""

    model_config = ConfigDict()

    node_id: NodeId
    zone_id: ZoneId
    window_start: datetime
    window_end: datetime
    signals: tuple[PerceptionSignal, ...] = Field(min_length=1)
    weights: tuple[ModalityWeight, ...] = Field(default_factory=tuple)
