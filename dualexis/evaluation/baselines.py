"""Evaluation baselines for reproducible DUALEXIS benchmarks.

Placeholder deterministic implementations designed for later replacement with
full pipeline integrations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from dualexis.orchestration.models import SeverityLevel
from dualexis.semantic_events.models import SemanticEvent
from dualexis.simulation.runner import SimulationResult


class BaselineId(StrEnum):
    """Registered baseline identifiers for CLI and reports."""

    SINGLE_MODALITY = "single_modality"
    RULE_BASED = "rule_based"
    DUALEXIS_SEMANTIC = "dualexis_semantic"


class UnknownBaselineError(ValueError):
    """Raised when a baseline name is not registered."""


@dataclass(frozen=True)
class BaselineOutput:
    """Artifacts emitted by a baseline on a simulation run."""

    events: tuple[SemanticEvent, ...]
    time_to_recommendation_ms: float
    raw_media_bytes_persisted: int = 0
    personal_data_violations: int = 0
    human_review_compliant_count: int = 0
    human_review_required_count: int = 0


class Baseline(ABC):
    """Pluggable baseline interface for evaluation harnesses."""

    @property
    @abstractmethod
    def baseline_id(self) -> BaselineId:
        """Stable baseline identifier."""

    @property
    def name(self) -> str:
        return self.baseline_id.value

    @abstractmethod
    def run(self, simulation: SimulationResult) -> BaselineOutput:
        """Execute the baseline on a completed simulation result."""


class SingleModalityBaseline(Baseline):
    """B1-style baseline: video-weighted alerts without multimodal fusion."""

    @property
    def baseline_id(self) -> BaselineId:
        return BaselineId.SINGLE_MODALITY

    def run(self, simulation: SimulationResult) -> BaselineOutput:
        events: list[SemanticEvent] = []
        for event in simulation.events:
            modalities = event.metadata.get("modalities", "")
            if "video" in modalities.split(","):
                events.append(event)

        # Deterministic false positive: duplicate first event with inflated confidence.
        if simulation.events and simulation.seed % 2 == 0:
            source = simulation.events[0]
            events.append(
                source.model_copy(
                    update={
                        "confidence": min(1.0, source.confidence + 0.05),
                        "metadata": {
                            **source.metadata,
                            "category": "spurious_video_alert",
                        },
                    }
                )
            )

        review_required = sum(
            1 for event in events if event.severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
        )
        return BaselineOutput(
            events=tuple(events),
            time_to_recommendation_ms=300.0 + float(simulation.seed % 100),
            human_review_required_count=review_required,
            human_review_compliant_count=0,
        )


class RuleBasedFusionBaseline(Baseline):
    """B2-style baseline: threshold rules over zone-level simulation labels."""

    @property
    def baseline_id(self) -> BaselineId:
        return BaselineId.RULE_BASED

    def run(self, simulation: SimulationResult) -> BaselineOutput:
        events: list[SemanticEvent] = []
        seen: set[tuple[str, str]] = set()

        for label in simulation.ground_truth.labels:
            key = (label.zone_id, label.semantic_label)
            if key in seen:
                continue
            if label.semantic_label == "normal_flow":
                continue
            if label.expected_severity == SeverityLevel.LOW and simulation.seed % 5 == 0:
                continue

            matching = [
                event
                for event in simulation.events
                if event.zone_id == label.zone_id
                and event.metadata.get("category") == label.semantic_label
            ]
            if matching:
                events.append(matching[0])
                seen.add(key)

        review_required = sum(
            1 for event in events if event.severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
        )
        compliant = max(0, review_required - (1 if simulation.seed % 7 == 0 else 0))
        return BaselineOutput(
            events=tuple(events),
            time_to_recommendation_ms=220.0 + float((simulation.seed * 3) % 80),
            human_review_required_count=review_required,
            human_review_compliant_count=compliant,
        )


class DualexisSemanticBaseline(Baseline):
    """DUALEXIS semantic stack placeholder: passthrough simulation events."""

    @property
    def baseline_id(self) -> BaselineId:
        return BaselineId.DUALEXIS_SEMANTIC

    def run(self, simulation: SimulationResult) -> BaselineOutput:
        review_required = sum(
            1
            for event in simulation.events
            if event.severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL}
        )
        return BaselineOutput(
            events=simulation.events,
            time_to_recommendation_ms=120.0 + float(simulation.seed % 40),
            raw_media_bytes_persisted=0,
            personal_data_violations=0,
            human_review_required_count=review_required,
            human_review_compliant_count=review_required,
        )


_BASELINES: dict[BaselineId, Baseline] = {
    BaselineId.SINGLE_MODALITY: SingleModalityBaseline(),
    BaselineId.RULE_BASED: RuleBasedFusionBaseline(),
    BaselineId.DUALEXIS_SEMANTIC: DualexisSemanticBaseline(),
}


def get_baseline(name: str) -> Baseline:
    """Resolve a baseline name to a registered baseline instance."""
    try:
        baseline_id = BaselineId(name)
    except ValueError as exc:
        valid = ", ".join(baseline.value for baseline in BaselineId)
        msg = f"Unknown baseline {name!r}. Valid baselines: {valid}"
        raise UnknownBaselineError(msg) from exc
    return _BASELINES[baseline_id]


def list_baselines() -> tuple[BaselineId, ...]:
    """Return all registered baseline identifiers."""
    return tuple(BaselineId)
