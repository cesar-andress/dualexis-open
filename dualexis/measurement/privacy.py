"""Privacy-related measurement extraction."""

from __future__ import annotations

from dualexis.evaluation.metrics import (
    compute_human_review_compliance_rate,
    compute_personal_data_exposure_score,
    compute_raw_data_retention_score,
)
from dualexis.evaluation.protocol import ProtocolExecutionResult
from dualexis.pipeline.models import PipelineOutput


def protocol_result_from_pipeline(output: PipelineOutput) -> ProtocolExecutionResult:
    """Map pipeline output to the evaluation protocol result shape."""
    review_required = sum(1 for rec in output.recommendations if rec.requires_human_review)
    review_compliant = sum(
        1
        for rec in output.recommendations
        if rec.requires_human_review and rec.human_review_status.value != "not_required"
    )
    privacy = output.privacy_report
    return ProtocolExecutionResult(
        events=output.normalized_events,
        end_to_end_latency_ms=0.0,
        time_to_recommendation_ms=0.0,
        graph_update_latency_ms=0.0,
        raw_media_bytes_persisted=privacy.raw_media_bytes_persisted,
        personal_data_violations=privacy.personal_data_violations,
        privacy_violation_count=len(privacy.violations),
        human_review_compliant_count=review_compliant,
        human_review_required_count=review_required,
    )


def extract_privacy_metrics(output: PipelineOutput) -> dict[str, float | int]:
    """Return privacy metric fields always present in measurement reports."""
    execution = protocol_result_from_pipeline(output)
    return {
        "privacy_violation_count": execution.privacy_violation_count,
        "raw_media_retention_score": compute_raw_data_retention_score(
            execution,
            output.normalized_events,
        ),
        "personal_data_exposure_score": compute_personal_data_exposure_score(execution),
        "human_review_compliance_rate": compute_human_review_compliance_rate(execution),
    }


__all__ = ["extract_privacy_metrics", "protocol_result_from_pipeline"]
