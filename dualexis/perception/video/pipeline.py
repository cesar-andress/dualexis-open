"""Video perception pipeline — zone-level activity, no facial recognition."""

from dualexis.perception.base import BasePerceptionPipeline
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal


class VideoPerceptionPipeline(BasePerceptionPipeline):
    """Placeholder video pipeline producing anonymized zone-level descriptors."""

    def __init__(self, node_id: str) -> None:
        super().__init__(node_id, Modality.VIDEO)

    async def _extract_signals(self, frame: PerceptionFrame) -> list[PerceptionSignal]:
        zone = self._build_zone_descriptor(frame, occupancy=12, activity=0.35)
        signal = self._make_signal(
            frame,
            zone,
            confidence=0.72,
            labels=("crowd_density_moderate", "movement_detected"),
            features={"motion_magnitude": 0.35, "density_score": 0.48},
        )
        return [signal]
