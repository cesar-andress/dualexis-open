"""Pipeline execution configuration (ablations and validation runs)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PipelineRunConfig(BaseModel):
    """Toggle layers for ablation studies on synthetic inputs."""

    model_config = ConfigDict(frozen=True)

    enable_privacy_runtime: bool = Field(
        default=True,
        description="When False, skip L1 validation/sanitization (ablation only).",
    )
    enable_temporal_graph: bool = Field(
        default=True,
        description="When False, skip L4 graph ingestion and context assembly.",
    )
    enable_explanation_layer: bool = Field(
        default=True,
        description="When False, omit explanations and L5 reasoning outputs.",
    )
    enable_sssg: bool = Field(
        default=True,
        description="When True, run Semantic Safety State Graph transitions (SSSG).",
    )


DEFAULT_PIPELINE_RUN_CONFIG = PipelineRunConfig()

__all__ = ["DEFAULT_PIPELINE_RUN_CONFIG", "PipelineRunConfig"]
