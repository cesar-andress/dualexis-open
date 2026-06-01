"""Default multimodal fusion engine — weighted semantic combination."""

from __future__ import annotations

from uuid import uuid4

from dualexis.core.interfaces import FusionEngine
from dualexis.schemas.domain import (
    ConfidenceScore,
    EventSource,
    FusionResult,
    LocationReference,
    PrivacyLevel,
)
from dualexis.schemas.fusion import FusionInput, ModalityWeight


class DefaultFusionEngine(FusionEngine):
    """Fuses perception signals using configurable modality weights."""

    def __init__(self, default_weights: dict[str, float] | None = None) -> None:
        self._default_weights = default_weights or {
            "video": 0.4,
            "audio": 0.35,
            "sensor": 0.25,
        }

    async def fuse(self, inputs: FusionInput) -> FusionResult:
        weights = self._resolve_weights(inputs.weights)
        label_scores: dict[str, float] = {}
        modality_contributions: dict[str, float] = {}
        signal_ids: list[str] = []

        for signal in inputs.signals:
            modality = signal.modality.value
            weight = weights.get(modality, 0.1)
            modality_contributions[modality] = (
                modality_contributions.get(modality, 0.0) + weight * signal.confidence
            )
            signal_ids.append(signal.signal_id)
            for label in signal.labels:
                label_scores[label] = label_scores.get(label, 0.0) + weight * signal.confidence

        sorted_labels = sorted(label_scores, key=label_scores.get, reverse=True)  # type: ignore[arg-type]
        fused_confidence = min(
            sum(modality_contributions.values()) / max(len(modality_contributions), 1),
            1.0,
        )
        fused_confidence = round(fused_confidence, 4)
        label_text = ", ".join(sorted_labels[:5]) if sorted_labels else "no labels"
        modalities = ", ".join(sorted(modality_contributions.keys()))

        return FusionResult(
            fusion_id=str(uuid4()),
            source=EventSource(
                node_id=inputs.node_id,
                modality="multimodal",
                pipeline_id="default-fusion-engine",
            ),
            location=LocationReference(
                zone_id=inputs.zone_id,
                zone_label=f"zone-{inputs.zone_id}",
            ),
            confidence=ConfidenceScore(
                value=fused_confidence,
                rationale=(
                    f"Weighted fusion across modalities ({modalities}) "
                    f"produced labels: {label_text}"
                ),
            ),
            fused_labels=tuple(sorted_labels[:5]) if sorted_labels else ("unknown",),
            explanation=(
                f"Multimodal semantic fusion combined {len(signal_ids)} normalized "
                f"signals in zone '{inputs.zone_id}' with confidence {fused_confidence:.2f}."
            ),
            signal_ids=tuple(signal_ids),
            modality_contributions=modality_contributions,
            privacy_level=PrivacyLevel.INTERNAL,
        )

    def _resolve_weights(self, overrides: tuple[ModalityWeight, ...]) -> dict[str, float]:
        weights = dict(self._default_weights)
        for override in overrides:
            weights[override.modality] = override.weight
        return weights
