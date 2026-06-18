"""Shared models for audit-comparison trace exports."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExportFormat(StrEnum):
    """Baseline trace export formats derived from the same TSGG run record."""

    TSGG = "tsgg"
    FLAT_JSON = "flat_json"
    PROV = "prov"
    XES = "xes"


PRIMARY_AUDIT_FORMATS: tuple[ExportFormat, ...] = (
    ExportFormat.TSGG,
    ExportFormat.FLAT_JSON,
    ExportFormat.PROV,
)


class AuditTraceExports(BaseModel):
    """All export formats for one (scenario, seed) run."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    seed: int
    tsgg: dict[str, Any] = Field(default_factory=dict)
    flat_json: dict[str, Any] = Field(default_factory=dict)
    prov: dict[str, Any] = Field(default_factory=dict)
    xes: dict[str, Any] = Field(default_factory=dict)

    def payload(self, export_format: ExportFormat) -> dict[str, Any]:
        return {
            ExportFormat.TSGG: self.tsgg,
            ExportFormat.FLAT_JSON: self.flat_json,
            ExportFormat.PROV: self.prov,
            ExportFormat.XES: self.xes,
        }[export_format]


__all__ = ["AuditTraceExports", "ExportFormat", "PRIMARY_AUDIT_FORMATS"]
