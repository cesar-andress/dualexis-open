"""Aggregate metrics for audit-comparison experiments."""

from __future__ import annotations

from dualexis.evaluation.audit_tasks.models import TaskEvalResult, TaskGold, ViolationMetrics


def query_success_rate(results: list[TaskEvalResult]) -> float:
    applicable = [result for result in results if result.applicable]
    if not applicable:
        return 1.0
    successes = sum(1 for result in applicable if result.success)
    return round(successes / len(applicable), 4)


def completeness_score(result: TaskEvalResult, gold: TaskGold) -> float:
    if not gold.required_fields or not result.applicable:
        return 1.0
    if not result.extracted_facts:
        return 0.0
    matched = sum(1 for fact in gold.gold_facts if any(fact.split(":")[0] in ef for ef in result.extracted_facts))
    if not gold.gold_facts:
        return 1.0 if result.success else 0.0
    return round(min(1.0, matched / len(gold.gold_facts)), 4)


def information_loss_ratio(result: TaskEvalResult, gold: TaskGold) -> float:
    if not gold.gold_facts:
        return 0.0
    if not result.extracted_facts:
        return 1.0
    overlap = gold.gold_facts & result.extracted_facts
    if not overlap:
        overlap = {
            fact
            for fact in gold.gold_facts
            if any(fact.split(":")[-1] in extracted for extracted in result.extracted_facts)
        }
    preserved = len(overlap) / len(gold.gold_facts)
    return round(max(0.0, min(1.0, 1.0 - preserved)), 4)


def violation_detection_metrics(
    *,
    predicted_positive: bool,
    expected_positive: bool,
) -> ViolationMetrics:
    tp = int(predicted_positive and expected_positive)
    fp = int(predicted_positive and not expected_positive)
    fn = int(not predicted_positive and expected_positive)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return ViolationMetrics(precision=round(precision, 4), recall=round(recall, 4), f1=round(f1, 4))


def mean_query_hops(results: list[TaskEvalResult]) -> float:
    applicable = [result for result in results if result.applicable]
    if not applicable:
        return 0.0
    return round(sum(result.query_hops for result in applicable) / len(applicable), 4)


__all__ = [
    "completeness_score",
    "information_loss_ratio",
    "mean_query_hops",
    "query_success_rate",
    "violation_detection_metrics",
]
