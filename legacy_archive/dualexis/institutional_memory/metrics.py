"""Institutional memory metrics."""

from __future__ import annotations

import statistics

from dualexis.institutional_memory.models import (
    InstitutionalMemoryGraph,
    InstitutionalMemoryMetrics,
)
from dualexis.tsgg.models import TsggRunRecord


def compute_institutional_memory_metrics(
    graph: InstitutionalMemoryGraph,
    *,
    run_records: list[TsggRunRecord],
) -> InstitutionalMemoryMetrics:
    memory_coverage = _memory_coverage(run_records)
    pattern_recurrence = _pattern_recurrence(graph)
    governance_learning_index = _governance_learning_index(
        memory_coverage, pattern_recurrence, graph
    )
    return InstitutionalMemoryMetrics(
        memory_coverage=memory_coverage,
        pattern_recurrence=pattern_recurrence,
        governance_learning_index=governance_learning_index,
    )


def _memory_coverage(run_records: list[TsggRunRecord]) -> float:
    if not run_records:
        return 0.0
    covered = sum(
        1
        for record in run_records
        if record.governance_traces or record.pipeline_output.recommendations
    )
    return round(covered / len(run_records), 4)


def _pattern_recurrence(graph: InstitutionalMemoryGraph) -> float:
    ratios: list[float] = []
    ratios.extend(p.support_ratio for p in graph.governance_patterns)
    ratios.extend(p.support_ratio for p in graph.escalation_chains)
    ratios.extend(p.support_ratio for p in graph.override_patterns)
    if not ratios:
        return 0.0
    return round(statistics.mean(ratios), 4)


def _governance_learning_index(
    coverage: float,
    recurrence: float,
    graph: InstitutionalMemoryGraph,
) -> float:
    compliance_rates: list[float] = [p.policy_compliance_rate for p in graph.governance_patterns]
    compliance = statistics.mean(compliance_rates) if compliance_rates else 0.5
    near_miss_penalty = min(1.0, len(graph.near_miss_patterns) / max(1, graph.trace_count))
    learning = (
        0.35 * coverage + 0.30 * recurrence + 0.25 * compliance + 0.10 * (1.0 - near_miss_penalty)
    )
    return round(max(0.0, min(1.0, learning)), 4)


__all__ = ["compute_institutional_memory_metrics"]
