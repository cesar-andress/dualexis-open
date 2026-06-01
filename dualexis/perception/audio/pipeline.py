"""Audio perception pipeline — acoustic event detection, no speaker ID."""

from dualexis.perception.base import BasePerceptionPipeline
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal


class AudioPerceptionPipeline(BasePerceptionPipeline):
    """Placeholder audio pipeline detecting acoustic events without speaker identification."""

    def __init__(self, node_id: str) -> None:
        super().__init__(node_id, Modality.AUDIO)

    async def _extract_signals(self, frame: PerceptionFrame) -> list[PerceptionSignal]:
        zone = self._build_zone_descriptor(frame, occupancy=0, activity=0.55)
        signal = self._make_signal(
            frame,
            zone,
            confidence=0.68,
            labels=("elevated_noise_level",),
            features={"decibel_estimate": 72.5, "spectral_energy": 0.61},
        )
        return [signal]
