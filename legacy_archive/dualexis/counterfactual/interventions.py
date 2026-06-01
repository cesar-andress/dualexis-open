"""Apply counterfactual interventions to SSSG evidence bundles."""

from __future__ import annotations

from dataclasses import dataclass

from dualexis.sssg.models import EvidenceKind, EvidenceRecord
from dualexis.counterfactual.models import CounterfactualInterventionKind

DENSITY_SAFE_THRESHOLD = 0.35
EXIT_RECOVERED_THROUGHPUT = 0.85
AUDIO_CLEARED_LEVEL = 0.05


@dataclass(frozen=True, slots=True)
class InterventionSpec:
    kind: CounterfactualInterventionKind
    hypothesis: str
    question: str


STANDARD_INTERVENTIONS: tuple[InterventionSpec, ...] = (
    InterventionSpec(
        kind=CounterfactualInterventionKind.DENSITY_BELOW_THRESHOLD,
        hypothesis="density had remained below threshold",
        question="What would have happened if zone density had remained below threshold?",
    ),
    InterventionSpec(
        kind=CounterfactualInterventionKind.EXIT_THROUGHPUT_RECOVERED,
        hypothesis="exit throughput had recovered",
        question="What would have happened if exit throughput had recovered?",
    ),
    InterventionSpec(
        kind=CounterfactualInterventionKind.AUDIO_STRESS_CLEARED,
        hypothesis="audio stress had disappeared",
        question="What would have happened if audio stress had disappeared?",
    ),
)


def apply_intervention(
    evidence: tuple[EvidenceRecord, ...],
    intervention: CounterfactualInterventionKind,
    *,
    zone_id: str,
) -> tuple[EvidenceRecord, ...]:
    """Return a copy of evidence with the counterfactual perturbation applied."""
    perturbed: list[EvidenceRecord] = []
    for record in evidence:
        if intervention == CounterfactualInterventionKind.DENSITY_BELOW_THRESHOLD:
            if record.kind == EvidenceKind.ZONE_DENSITY and record.zone_id == zone_id:
                perturbed.append(
                    record.model_copy(
                        update={
                            "metric_value": DENSITY_SAFE_THRESHOLD,
                            "description": (
                                f"Counterfactual: zone density {DENSITY_SAFE_THRESHOLD:.2f} "
                                "(below threshold)"
                            ),
                        }
                    )
                )
                continue
        if intervention == CounterfactualInterventionKind.EXIT_THROUGHPUT_RECOVERED:
            if record.kind == EvidenceKind.EXIT_THROUGHPUT:
                perturbed.append(
                    record.model_copy(
                        update={
                            "metric_value": EXIT_RECOVERED_THROUGHPUT,
                            "description": (
                                f"Counterfactual: exit throughput recovered "
                                f"to {EXIT_RECOVERED_THROUGHPUT:.2f}"
                            ),
                        }
                    )
                )
                continue
        if intervention == CounterfactualInterventionKind.AUDIO_STRESS_CLEARED:
            if record.kind == EvidenceKind.ZONE_AUDIO and record.zone_id == zone_id:
                perturbed.append(
                    record.model_copy(
                        update={
                            "metric_value": AUDIO_CLEARED_LEVEL,
                            "description": "Counterfactual: audio stress cleared",
                        }
                    )
                )
                continue
        perturbed.append(record)
    return tuple(perturbed)


def perturbed_metric_snapshot(
    evidence: tuple[EvidenceRecord, ...],
    intervention: CounterfactualInterventionKind,
    *,
    zone_id: str,
) -> dict[str, float]:
    """Metrics after intervention for export."""
    updated = apply_intervention(evidence, intervention, zone_id=zone_id)
    snapshot: dict[str, float] = {}
    for record in updated:
        if record.metric_value is None:
            continue
        key = f"{record.kind.value}:{record.zone_id}"
        snapshot[key] = record.metric_value
    return snapshot


__all__ = [
    "AUDIO_CLEARED_LEVEL",
    "DENSITY_SAFE_THRESHOLD",
    "EXIT_RECOVERED_THROUGHPUT",
    "STANDARD_INTERVENTIONS",
    "InterventionSpec",
    "apply_intervention",
    "perturbed_metric_snapshot",
]
