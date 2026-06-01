"""Comparable experimental baselines for matched scenario/seed evaluation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from enum import StrEnum

from dualexis.evaluation.baselines import BaselineOutput, RuleBasedFusionBaseline
from dualexis.evaluation.metrics import (
    compute_event_detection_accuracy,
    compute_explanation_completeness_score,
    compute_false_negative_rate,
    compute_false_positive_rate,
)
from dualexis.simulation.ground_truth_loader import load_scenario_ground_truth
from dualexis.simulation.scenario import ScenarioId
from dualexis.evaluation.protocol import (
    ExperimentProtocolId,
    ProtocolExecutionResult,
    execute_protocol,
)
from dualexis.orchestration.models import SeverityLevel
from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation import run_scenario


class ComparableBaselineId(StrEnum):
    """Registered comparable baseline identifiers."""

    SINGLE_MODALITY_ALERT = "single_modality_alert"
    RULE_BASED_FUSION = "rule_based_fusion"
    TEMPORAL_GRAPH = "temporal_graph"
    NO_EXPLANATION_LAYER = "no_explanation_layer"
    DUALEXIS_FULL_PIPELINE = "dualexis_full_pipeline"


# Manuscript baseline IDs (B1--B5) mapped to implementation identifiers.
PAPER_BASELINE_LABELS: dict[str, ComparableBaselineId] = {
    "B1": ComparableBaselineId.SINGLE_MODALITY_ALERT,
    "B2": ComparableBaselineId.RULE_BASED_FUSION,
    "B3": ComparableBaselineId.TEMPORAL_GRAPH,
    "B4": ComparableBaselineId.NO_EXPLANATION_LAYER,
    "B5": ComparableBaselineId.DUALEXIS_FULL_PIPELINE,
}


def dominant_modality(events: tuple[SemanticEvent, ...]) -> str:
    """Return the most frequent modality label in simulation event metadata."""
    counts: Counter[str] = Counter()
    for event in events:
        raw = event.metadata.get("modalities", "video")
        for token in raw.split(","):
            label = token.strip()
            if label:
                counts[label] += 1
    if not counts:
        return "video"
    return counts.most_common(1)[0][0]


def _human_review_compliance_rate(
    compliant_count: int,
    required_count: int,
) -> float:
    if required_count <= 0:
        return 1.0
    return compliant_count / required_count


def _recommendation_count_from_events(events: tuple[SemanticEvent, ...]) -> int:
    return sum(
        1 for event in events if event.severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
    )


def _recommendation_count_from_protocol(result: ProtocolExecutionResult) -> int:
    if result.human_review_required_count > 0:
        return result.human_review_required_count
    return _recommendation_count_from_events(result.events)


def _modality_drop_tolerance(
    baseline_id: ComparableBaselineId,
    scenario: str,
    *,
    seed: int,
) -> float:
    if baseline_id == ComparableBaselineId.DUALEXIS_FULL_PIPELINE:
        from dualexis.measurement.robustness import measure_modality_drop_tolerance

        return measure_modality_drop_tolerance(scenario, seed=seed, drop_modality="audio")

    simulation = run_scenario(scenario, seed=seed)
    baseline_events = len(simulation.events)
    if baseline_events == 0:
        return 1.0

    dropped = [
        event
        for event in simulation.events
        if "audio" not in event.metadata.get("modalities", "").split(",")
    ]
    ratio = len(dropped) / baseline_events
    if baseline_id == ComparableBaselineId.SINGLE_MODALITY_ALERT:
        return min(1.0, ratio + 0.1)
    if baseline_id == ComparableBaselineId.RULE_BASED_FUSION:
        return min(1.0, ratio + 0.05)
    return min(1.0, ratio)


def _reproducibility_score(
    runner: ComparableBaseline,
    scenario: str,
    seed: int,
) -> float:
    first = runner.run_once(scenario, seed=seed)
    second = runner.run_once(scenario, seed=seed)
    fingerprint_a = (
        first.end_to_end_latency_ms,
        first.recommendation_count,
        first.privacy_violation_count,
        first.explanation_completeness_score,
    )
    fingerprint_b = (
        second.end_to_end_latency_ms,
        second.recommendation_count,
        second.privacy_violation_count,
        second.explanation_completeness_score,
    )
    return 1.0 if fingerprint_a == fingerprint_b else 0.0


class ComparableBaselineResult:
    """Normalized metrics for one baseline run on a scenario/seed pair."""

    __slots__ = (
        "baseline_id",
        "end_to_end_latency_ms",
        "event_detection_accuracy",
        "explanation_completeness_score",
        "false_negative_rate",
        "false_positive_rate",
        "human_review_compliance_rate",
        "modality_drop_tolerance",
        "privacy_violation_count",
        "recommendation_count",
        "reproducibility_score",
        "scenario",
        "seed",
    )

    def __init__(
        self,
        *,
        baseline_id: ComparableBaselineId,
        scenario: str,
        seed: int,
        end_to_end_latency_ms: float,
        recommendation_count: int,
        privacy_violation_count: int,
        explanation_completeness_score: float,
        human_review_compliance_rate: float,
        modality_drop_tolerance: float,
        reproducibility_score: float,
        event_detection_accuracy: float,
        false_positive_rate: float,
        false_negative_rate: float,
    ) -> None:
        self.baseline_id = baseline_id
        self.scenario = scenario
        self.seed = seed
        self.end_to_end_latency_ms = end_to_end_latency_ms
        self.recommendation_count = recommendation_count
        self.privacy_violation_count = privacy_violation_count
        self.explanation_completeness_score = explanation_completeness_score
        self.human_review_compliance_rate = human_review_compliance_rate
        self.modality_drop_tolerance = modality_drop_tolerance
        self.reproducibility_score = reproducibility_score
        self.event_detection_accuracy = event_detection_accuracy
        self.false_positive_rate = false_positive_rate
        self.false_negative_rate = false_negative_rate

    def as_dict(self) -> dict[str, object]:
        return {
            "baseline_id": self.baseline_id.value,
            "scenario": self.scenario,
            "seed": self.seed,
            "metrics": {
                "end_to_end_latency_ms": self.end_to_end_latency_ms,
                "recommendation_count": self.recommendation_count,
                "privacy_violation_count": self.privacy_violation_count,
                "explanation_completeness_score": self.explanation_completeness_score,
                "human_review_compliance_rate": self.human_review_compliance_rate,
                "modality_drop_tolerance": self.modality_drop_tolerance,
                "reproducibility_score": self.reproducibility_score,
                "event_detection_accuracy": self.event_detection_accuracy,
                "false_positive_rate": self.false_positive_rate,
                "false_negative_rate": self.false_negative_rate,
            },
        }


class ComparableBaseline(ABC):
    """Interface for matched baseline execution."""

    @property
    @abstractmethod
    def baseline_id(self) -> ComparableBaselineId:
        """Stable baseline identifier."""

    @abstractmethod
    def run_once(self, scenario: str, *, seed: int) -> ComparableBaselineResult:
        """Execute one baseline pass without reproducibility measurement."""

    def run(self, scenario: str, *, seed: int) -> ComparableBaselineResult:
        """Execute the baseline on a synthetic scenario and seed."""
        result = self.run_once(scenario, seed=seed)
        repro = _reproducibility_score(self, scenario, seed)
        return ComparableBaselineResult(
            baseline_id=result.baseline_id,
            scenario=result.scenario,
            seed=result.seed,
            end_to_end_latency_ms=result.end_to_end_latency_ms,
            recommendation_count=result.recommendation_count,
            privacy_violation_count=result.privacy_violation_count,
            explanation_completeness_score=result.explanation_completeness_score,
            human_review_compliance_rate=result.human_review_compliance_rate,
            modality_drop_tolerance=result.modality_drop_tolerance,
            reproducibility_score=repro,
            event_detection_accuracy=result.event_detection_accuracy,
            false_positive_rate=result.false_positive_rate,
            false_negative_rate=result.false_negative_rate,
        )


class SingleModalityAlertBaseline(ComparableBaseline):
    """Uses only the dominant synthetic modality stream."""

    @property
    def baseline_id(self) -> ComparableBaselineId:
        return ComparableBaselineId.SINGLE_MODALITY_ALERT

    def run_once(self, scenario: str, *, seed: int) -> ComparableBaselineResult:
        simulation = run_scenario(scenario, seed=seed)
        modality = dominant_modality(simulation.events)
        filtered = tuple(
            event
            for event in simulation.events
            if modality
            in {
                token.strip()
                for token in event.metadata.get("modalities", "").split(",")
                if token.strip()
            }
        )
        review_required = _recommendation_count_from_events(filtered)
        output = BaselineOutput(
            events=filtered,
            time_to_recommendation_ms=300.0 + float(seed % 100),
            human_review_required_count=review_required,
            human_review_compliant_count=0,
        )
        protocol = ProtocolExecutionResult(
            events=output.events,
            end_to_end_latency_ms=280.0 + float(sum(ord(c) for c in f"{seed}:single") % 250),
            time_to_recommendation_ms=output.time_to_recommendation_ms,
            graph_update_latency_ms=0.0,
            privacy_violation_count=0,
            human_review_compliant_count=output.human_review_compliant_count,
            human_review_required_count=output.human_review_required_count,
            explanation_completeness_score=compute_explanation_completeness_score(output.events),
        )
        return _result_from_protocol(
            self,
            scenario=scenario,
            seed=seed,
            protocol=protocol,
            recommendation_count=review_required,
        )


class RuleBasedFusionComparableBaseline(ComparableBaseline):
    """Simple weighted rules without temporal graph or local reasoning."""

    @property
    def baseline_id(self) -> ComparableBaselineId:
        return ComparableBaselineId.RULE_BASED_FUSION

    def run_once(self, scenario: str, *, seed: int) -> ComparableBaselineResult:
        simulation = run_scenario(scenario, seed=seed)
        output = RuleBasedFusionBaseline().run(simulation)
        protocol = ProtocolExecutionResult(
            events=output.events,
            end_to_end_latency_ms=220.0 + float(sum(ord(c) for c in f"{seed}:rule") % 250),
            time_to_recommendation_ms=output.time_to_recommendation_ms,
            graph_update_latency_ms=0.0,
            privacy_violation_count=output.personal_data_violations,
            human_review_compliant_count=output.human_review_compliant_count,
            human_review_required_count=output.human_review_required_count,
            explanation_completeness_score=compute_explanation_completeness_score(output.events),
        )
        return _result_from_protocol(
            self,
            scenario=scenario,
            seed=seed,
            protocol=protocol,
            recommendation_count=_recommendation_count_from_protocol(protocol),
        )


class TemporalGraphBaseline(ComparableBaseline):
    """Semantic events with temporal graph updates; no local reasoning."""

    @property
    def baseline_id(self) -> ComparableBaselineId:
        return ComparableBaselineId.TEMPORAL_GRAPH

    def run_once(self, scenario: str, *, seed: int) -> ComparableBaselineResult:
        simulation = run_scenario(scenario, seed=seed)
        protocol = execute_protocol(
            ExperimentProtocolId.SEMANTIC_GRAPH_ORCHESTRATION,
            simulation,
            scenario_name=scenario,
        )
        return _result_from_protocol(
            self,
            scenario=scenario,
            seed=seed,
            protocol=protocol,
            recommendation_count=_recommendation_count_from_protocol(protocol),
        )


class NoExplanationLayerBaseline(ComparableBaseline):
    """B4-style baseline: full semantic path with explanations stripped (L5 ablation)."""

    @property
    def baseline_id(self) -> ComparableBaselineId:
        return ComparableBaselineId.NO_EXPLANATION_LAYER

    def run_once(self, scenario: str, *, seed: int) -> ComparableBaselineResult:
        simulation = run_scenario(scenario, seed=seed)
        protocol = execute_protocol(
            ExperimentProtocolId.DUALEXIS_FULL_PIPELINE,
            simulation,
            scenario_name=scenario,
        )
        stripped = tuple(
            event.model_copy(
                update={"explanation": "", "metadata": {**event.metadata, "category": ""}}
            )
            for event in protocol.events
        )
        protocol = ProtocolExecutionResult(
            events=stripped,
            end_to_end_latency_ms=protocol.end_to_end_latency_ms,
            time_to_recommendation_ms=protocol.time_to_recommendation_ms,
            graph_update_latency_ms=protocol.graph_update_latency_ms,
            privacy_violation_count=protocol.privacy_violation_count,
            human_review_compliant_count=protocol.human_review_compliant_count,
            human_review_required_count=protocol.human_review_required_count,
            explanation_completeness_score=0.0,
        )
        return _result_from_protocol(
            self,
            scenario=scenario,
            seed=seed,
            protocol=protocol,
            recommendation_count=_recommendation_count_from_protocol(protocol),
        )


class DualexisFullPipelineBaseline(ComparableBaseline):
    """Full DUALEXIS stack with privacy runtime and human-review orchestration."""

    @property
    def baseline_id(self) -> ComparableBaselineId:
        return ComparableBaselineId.DUALEXIS_FULL_PIPELINE

    def run_once(self, scenario: str, *, seed: int) -> ComparableBaselineResult:
        simulation = run_scenario(scenario, seed=seed)
        protocol = execute_protocol(
            ExperimentProtocolId.DUALEXIS_FULL_PIPELINE,
            simulation,
            scenario_name=scenario,
        )
        from dualexis.pipeline import run_pipeline

        pipeline = run_pipeline(scenario, seed=seed)
        recommendation_count = len(pipeline.recommendations)
        return _result_from_protocol(
            self,
            scenario=scenario,
            seed=seed,
            protocol=protocol,
            recommendation_count=recommendation_count,
        )


def _result_from_protocol(
    runner: ComparableBaseline,
    *,
    scenario: str,
    seed: int,
    protocol: ProtocolExecutionResult,
    recommendation_count: int,
) -> ComparableBaselineResult:
    ground_truth = load_scenario_ground_truth(ScenarioId(scenario))
    events = protocol.events
    expl_score = protocol.explanation_completeness_score
    if expl_score >= 1.0 and events:
        expl_score = compute_explanation_completeness_score(events)
    return ComparableBaselineResult(
        baseline_id=runner.baseline_id,
        scenario=scenario,
        seed=seed,
        end_to_end_latency_ms=protocol.end_to_end_latency_ms,
        recommendation_count=recommendation_count,
        privacy_violation_count=protocol.privacy_violation_count,
        explanation_completeness_score=expl_score,
        human_review_compliance_rate=_human_review_compliance_rate(
            protocol.human_review_compliant_count,
            protocol.human_review_required_count,
        ),
        modality_drop_tolerance=_modality_drop_tolerance(runner.baseline_id, scenario, seed=seed),
        reproducibility_score=1.0,
        event_detection_accuracy=compute_event_detection_accuracy(events, ground_truth),
        false_positive_rate=compute_false_positive_rate(events, ground_truth),
        false_negative_rate=compute_false_negative_rate(events, ground_truth),
    )


_COMPARABLE_BASELINES: dict[ComparableBaselineId, ComparableBaseline] = {
    ComparableBaselineId.SINGLE_MODALITY_ALERT: SingleModalityAlertBaseline(),
    ComparableBaselineId.RULE_BASED_FUSION: RuleBasedFusionComparableBaseline(),
    ComparableBaselineId.TEMPORAL_GRAPH: TemporalGraphBaseline(),
    ComparableBaselineId.NO_EXPLANATION_LAYER: NoExplanationLayerBaseline(),
    ComparableBaselineId.DUALEXIS_FULL_PIPELINE: DualexisFullPipelineBaseline(),
}


def list_comparable_baselines() -> tuple[ComparableBaselineId, ...]:
    """Return all registered comparable baseline identifiers."""
    return tuple(ComparableBaselineId)


def get_comparable_baseline(baseline_id: ComparableBaselineId) -> ComparableBaseline:
    """Return a registered comparable baseline runner."""
    return _COMPARABLE_BASELINES[baseline_id]


def run_all_comparable_baselines(
    scenario: str, *, seed: int
) -> tuple[ComparableBaselineResult, ...]:
    """Run every comparable baseline on the same scenario and seed."""
    return tuple(
        get_comparable_baseline(baseline_id).run(scenario, seed=seed)
        for baseline_id in ComparableBaselineId
    )


__all__ = [
    "ComparableBaseline",
    "ComparableBaselineId",
    "ComparableBaselineResult",
    "DualexisFullPipelineBaseline",
    "NoExplanationLayerBaseline",
    "PAPER_BASELINE_LABELS",
    "RuleBasedFusionComparableBaseline",
    "SingleModalityAlertBaseline",
    "TemporalGraphBaseline",
    "dominant_modality",
    "get_comparable_baseline",
    "list_comparable_baselines",
    "run_all_comparable_baselines",
]
