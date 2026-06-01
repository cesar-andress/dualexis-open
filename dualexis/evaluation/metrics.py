"""Evaluation metric computations for DUALEXIS benchmarks.

Operational definitions aligned with ``paper/sections/metrics.tex``.
This module computes scaffold values only; no experimental conclusions are implied.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from dualexis.evaluation.baselines import BaselineOutput
from dualexis.evaluation.protocol import ProtocolExecutionResult
from dualexis.evaluation.results import ExperimentMetrics
from dualexis.orchestration.models import SeverityLevel
from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.ground_truth import ScenarioGroundTruth

_HIGH_SEVERITIES = frozenset({SeverityLevel.HIGH, SeverityLevel.CRITICAL})


class EvaluationMetricSet(BaseModel):
    """Legacy metric bundle for baseline evaluation reports."""

    model_config = ConfigDict(frozen=True)

    event_count: float = Field(ge=0.0)
    average_confidence: float = Field(ge=0.0, le=1.0)
    high_severity_rate: float = Field(ge=0.0, le=1.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0)
    false_negative_rate: float = Field(ge=0.0, le=1.0)
    time_to_recommendation_ms: float = Field(ge=0.0)
    raw_media_retention_score: float = Field(ge=0.0, le=1.0)
    personal_data_exposure_score: float = Field(ge=0.0, le=1.0)
    human_review_compliance_rate: float = Field(ge=0.0, le=1.0)


def _event_label_key(event: SemanticEvent) -> tuple[str, str]:
    return (event.zone_id, event.metadata.get("category", ""))


def _ground_truth_label_key(label_zone_id: str, semantic_label: str) -> tuple[str, str]:
    return (label_zone_id, semantic_label)


def count_false_positives_and_negatives(
    predicted: tuple[SemanticEvent, ...],
    ground_truth: ScenarioGroundTruth,
) -> tuple[int, int]:
    """Count unmatched predictions (FP) and unmatched ground-truth labels (FN)."""
    predicted_counts = Counter(_event_label_key(event) for event in predicted)
    truth_counts = Counter(
        _ground_truth_label_key(label.zone_id, label.semantic_label)
        for label in ground_truth.labels
    )
    keys = set(predicted_counts) | set(truth_counts)
    false_positives = 0
    false_negatives = 0
    for key in keys:
        predicted_n = predicted_counts.get(key, 0)
        truth_n = truth_counts.get(key, 0)
        if predicted_n > truth_n:
            false_positives += predicted_n - truth_n
        if truth_n > predicted_n:
            false_negatives += truth_n - predicted_n
    return false_positives, false_negatives


def compute_event_count(events: tuple[SemanticEvent, ...]) -> float:
    return float(len(events))


def compute_average_confidence(events: tuple[SemanticEvent, ...]) -> float:
    if not events:
        return 0.0
    return sum(event.confidence for event in events) / len(events)


def compute_high_severity_rate(events: tuple[SemanticEvent, ...]) -> float:
    if not events:
        return 0.0
    high_count = sum(1 for event in events if event.severity in _HIGH_SEVERITIES)
    return high_count / len(events)


def compute_false_positive_rate(
    predicted: tuple[SemanticEvent, ...],
    ground_truth: ScenarioGroundTruth,
) -> float:
    false_positives, _ = count_false_positives_and_negatives(predicted, ground_truth)
    if not predicted:
        return 0.0
    return false_positives / len(predicted)


def compute_false_negative_rate(
    predicted: tuple[SemanticEvent, ...],
    ground_truth: ScenarioGroundTruth,
) -> float:
    _, false_negatives = count_false_positives_and_negatives(predicted, ground_truth)
    if not ground_truth.labels:
        return 0.0
    return false_negatives / len(ground_truth.labels)


def compute_event_detection_accuracy(
    predicted: tuple[SemanticEvent, ...],
    ground_truth: ScenarioGroundTruth,
) -> float:
    """Fraction of ground-truth labels matched by at least one predicted event."""
    if not ground_truth.labels:
        return 1.0 if not predicted else 0.0
    _, false_negatives = count_false_positives_and_negatives(predicted, ground_truth)
    true_positives = len(ground_truth.labels) - false_negatives
    return true_positives / len(ground_truth.labels)


def compute_explanation_completeness_score(events: tuple[SemanticEvent, ...]) -> float:
    if not events:
        return 0.0
    complete = 0
    for event in events:
        if event.zone_id and event.explanation.strip() and event.metadata.get("category"):
            complete += 1
    return complete / len(events)


def compute_raw_data_retention_score(
    execution: ProtocolExecutionResult,
    events: tuple[SemanticEvent, ...],
) -> float:
    """Return 1.0 when no raw media persists; lower values indicate retention risk."""
    if execution.raw_media_bytes_persisted > 0:
        normalized = min(1.0, execution.raw_media_bytes_persisted / 1_000_000.0)
        return max(0.0, 1.0 - normalized)
    if any(event.raw_media_persisted for event in events):
        return 0.0
    return 1.0


def _personal_data_exposure_from_execution(execution: ProtocolExecutionResult) -> float:
    """Lower is better; 0.0 indicates no observed exposure in the scaffold."""
    if execution.personal_data_violations <= 0:
        return 0.0
    return min(1.0, float(execution.personal_data_violations))


def _human_review_compliance_from_execution(execution: ProtocolExecutionResult) -> float:
    if execution.human_review_required_count <= 0:
        return 1.0
    return execution.human_review_compliant_count / execution.human_review_required_count


def compute_personal_data_exposure_score(execution: ProtocolExecutionResult) -> float:
    return _personal_data_exposure_from_execution(execution)


def compute_human_review_compliance_rate(execution: ProtocolExecutionResult) -> float:
    return _human_review_compliance_from_execution(execution)


def compute_experiment_metrics(
    execution: ProtocolExecutionResult,
    ground_truth: ScenarioGroundTruth,
) -> ExperimentMetrics:
    """Compute the full pre-registered experiment metric set."""
    events = execution.events
    explanation_score = execution.explanation_completeness_score
    if explanation_score == 1.0 and events:
        explanation_score = compute_explanation_completeness_score(events)

    return ExperimentMetrics(
        end_to_end_latency_ms=execution.end_to_end_latency_ms,
        event_detection_accuracy=compute_event_detection_accuracy(events, ground_truth),
        false_positive_rate=compute_false_positive_rate(events, ground_truth),
        false_negative_rate=compute_false_negative_rate(events, ground_truth),
        time_to_recommendation_ms=execution.time_to_recommendation_ms,
        explanation_completeness_score=explanation_score,
        human_review_compliance_rate=compute_human_review_compliance_rate(execution),
        raw_data_retention_score=compute_raw_data_retention_score(execution, events),
        personal_data_exposure_score=compute_personal_data_exposure_score(execution),
        privacy_violation_count=execution.privacy_violation_count,
        graph_update_latency_ms=execution.graph_update_latency_ms,
    )


def compute_raw_media_retention_score(
    output: BaselineOutput,
    events: tuple[SemanticEvent, ...],
) -> float:
    execution = ProtocolExecutionResult(
        events=output.events,
        end_to_end_latency_ms=0.0,
        time_to_recommendation_ms=output.time_to_recommendation_ms,
        graph_update_latency_ms=0.0,
        raw_media_bytes_persisted=output.raw_media_bytes_persisted,
        personal_data_violations=output.personal_data_violations,
        privacy_violation_count=output.personal_data_violations,
        human_review_compliant_count=output.human_review_compliant_count,
        human_review_required_count=output.human_review_required_count,
    )
    return compute_raw_data_retention_score(execution, events)


def compute_personal_data_exposure_score_from_baseline(output: BaselineOutput) -> float:
    execution = ProtocolExecutionResult(
        events=output.events,
        end_to_end_latency_ms=0.0,
        time_to_recommendation_ms=output.time_to_recommendation_ms,
        graph_update_latency_ms=0.0,
        personal_data_violations=output.personal_data_violations,
        privacy_violation_count=output.personal_data_violations,
    )
    return _personal_data_exposure_from_execution(execution)


def compute_human_review_compliance_rate_from_baseline(output: BaselineOutput) -> float:
    execution = ProtocolExecutionResult(
        events=output.events,
        end_to_end_latency_ms=0.0,
        time_to_recommendation_ms=output.time_to_recommendation_ms,
        graph_update_latency_ms=0.0,
        human_review_compliant_count=output.human_review_compliant_count,
        human_review_required_count=output.human_review_required_count,
    )
    return _human_review_compliance_from_execution(execution)


def compute_metrics(
    output: BaselineOutput,
    ground_truth: ScenarioGroundTruth,
) -> EvaluationMetricSet:
    """Compute the legacy metric set for a baseline run."""
    events = output.events
    execution = ProtocolExecutionResult(
        events=events,
        end_to_end_latency_ms=output.time_to_recommendation_ms + 50.0,
        time_to_recommendation_ms=output.time_to_recommendation_ms,
        graph_update_latency_ms=0.0,
        raw_media_bytes_persisted=output.raw_media_bytes_persisted,
        personal_data_violations=output.personal_data_violations,
        privacy_violation_count=output.personal_data_violations,
        human_review_compliant_count=output.human_review_compliant_count,
        human_review_required_count=output.human_review_required_count,
    )
    return EvaluationMetricSet(
        event_count=compute_event_count(events),
        average_confidence=compute_average_confidence(events),
        high_severity_rate=compute_high_severity_rate(events),
        false_positive_rate=compute_false_positive_rate(events, ground_truth),
        false_negative_rate=compute_false_negative_rate(events, ground_truth),
        time_to_recommendation_ms=output.time_to_recommendation_ms,
        raw_media_retention_score=compute_raw_data_retention_score(execution, events),
        personal_data_exposure_score=compute_personal_data_exposure_score(execution),
        human_review_compliance_rate=compute_human_review_compliance_rate(execution),
    )


__all__ = [
    "EvaluationMetricSet",
    "compute_average_confidence",
    "compute_event_count",
    "compute_event_detection_accuracy",
    "compute_experiment_metrics",
    "compute_explanation_completeness_score",
    "compute_false_negative_rate",
    "compute_false_positive_rate",
    "compute_high_severity_rate",
    "compute_human_review_compliance_rate",
    "compute_human_review_compliance_rate_from_baseline",
    "compute_metrics",
    "compute_personal_data_exposure_score",
    "compute_personal_data_exposure_score_from_baseline",
    "compute_raw_data_retention_score",
    "compute_raw_media_retention_score",
    "count_false_positives_and_negatives",
]
