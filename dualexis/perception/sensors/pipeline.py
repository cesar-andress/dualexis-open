"""Sensor perception pipeline — IoT and environmental sensors."""

from dualexis.perception.base import BasePerceptionPipeline
from dualexis.schemas.perception import Modality, PerceptionFrame, PerceptionSignal


class SensorPerceptionPipeline(BasePerceptionPipeline):
    """Placeholder sensor pipeline for environmental and IoT inputs."""

    def __init__(self, node_id: str) -> None:
        super().__init__(node_id, Modality.SENSOR)

    async def _extract_signals(self, frame: PerceptionFrame) -> list[PerceptionSignal]:
        zone = self._build_zone_descriptor(frame, occupancy=0, activity=0.1)
        signal = self._make_signal(
            frame,
            zone,
            confidence=0.91,
            labels=("door_sensor_triggered",),
            features={"contact_state": 1.0},
        )
        return [signal]
