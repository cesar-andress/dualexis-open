"""Formal DUALEXIS event taxonomy — zone-scoped, occupant-agnostic semantic categories.

Each ``TaxonomyEventType`` specifies required modalities, measurable features,
confidence expectations, severity mapping, privacy risk, evaluation metrics, and
example synthetic payloads. No event type requires occupant attribution or biometric data.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dualexis.orchestration.models import SeverityLevel
from dualexis.schemas.domain.validators import contains_forbidden_term


class EventCategory(StrEnum):
    """Top-level taxonomy grouping for semantic event types."""

    FLOW = "flow_events"
    ACCESS_AND_ROUTE = "access_and_route_events"
    AUDIO = "audio_events"
    SAFETY = "safety_events"
    MULTIMODAL = "multimodal_events"


class InputModality(StrEnum):
    """Perception modalities that may contribute to an event type."""

    VIDEO = "video"
    AUDIO = "audio"
    SENSOR = "sensor"


class TaxonomyPrivacyRisk(StrEnum):
    """Privacy exposure risk if mishandled — not an storage tier."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaxonomyEventType(StrEnum):
    """Canonical DUALEXIS semantic event identifiers (snake_case values)."""

    NORMAL_FLOW = "normal_flow"
    CROWD_ACCELERATION = "crowd_acceleration"
    CROWD_CONGESTION = "crowd_congestion"
    COUNTERFLOW = "counterflow"
    SUDDEN_DISPERSION = "sudden_dispersion"
    EXIT_BLOCKAGE = "exit_blockage"
    ROUTE_UNAVAILABLE = "route_unavailable"
    DOOR_FORCED = "door_forced"
    RESTRICTED_AREA_ENTRY = "restricted_area_entry"
    AUDIO_STRESS_SIGNAL = "audio_stress_signal"
    GLASS_BREAK = "glass_break"
    ALARM_DETECTED = "alarm_detected"
    IMPACT_SOUND = "impact_sound"
    VERBAL_HELP_REQUEST = "verbal_help_request"
    FALL_DETECTED = "fall_detected"
    PANIC_BUTTON_PRESSED = "panic_button_pressed"
    EVACUATION_SIGNAL = "evacuation_signal"
    FIRE_OR_SMOKE_SIGNAL = "fire_or_smoke_signal"
    MULTIMODAL_CONFIRMATION = "multimodal_confirmation"
    MULTIMODAL_CONFLICT = "multimodal_conflict"
    RISK_ESCALATION = "risk_escalation"
    RISK_DEESCALATION = "risk_deescalation"


class SeverityBand(BaseModel):
    """Maps a confidence interval to an operational severity level."""

    model_config = ConfigDict(frozen=True)

    min_confidence: float = Field(ge=0.0, le=1.0)
    max_confidence: float = Field(ge=0.0, le=1.0)
    severity: SeverityLevel

    @model_validator(mode="after")
    def validate_interval(self) -> SeverityBand:
        if self.min_confidence > self.max_confidence:
            msg = "min_confidence must not exceed max_confidence"
            raise ValueError(msg)
        return self


class SeverityMapping(BaseModel):
    """Ordered severity bands for confidence-to-severity translation."""

    model_config = ConfigDict(frozen=True)

    bands: tuple[SeverityBand, ...] = Field(min_length=1)

    def severity_for_confidence(self, confidence: float) -> SeverityLevel:
        clamped = max(0.0, min(1.0, confidence))
        for band in self.bands:
            if band.min_confidence <= clamped <= band.max_confidence:
                return band.severity
        return self.bands[-1].severity


class TaxonomyEventDefinition(BaseModel):
    """Formal specification for a single taxonomy event type."""

    model_config = ConfigDict(frozen=True)

    event_type: TaxonomyEventType
    category: EventCategory
    description: str = Field(min_length=1, max_length=2048)
    input_modalities: tuple[InputModality, ...] = Field(min_length=1)
    measurable_features: tuple[str, ...] = Field(min_length=1)
    expected_confidence_range: tuple[float, float]
    severity_mapping: SeverityMapping
    privacy_risk_level: TaxonomyPrivacyRisk
    evaluation_metric: str = Field(min_length=1, max_length=128)
    example_synthetic_payload: dict[str, str] = Field(default_factory=dict)
    requires_identity: bool = False
    requires_biometric: bool = False

    @field_validator("description", "evaluation_metric")
    @classmethod
    def reject_forbidden_terms_in_text(cls, value: str) -> str:
        matched = contains_forbidden_term(value)
        if matched is not None:
            msg = f"Field contains forbidden term '{matched}'"
            raise ValueError(msg)
        return value

    @field_validator("measurable_features")
    @classmethod
    def validate_features(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for feature in value:
            matched = contains_forbidden_term(feature)
            if matched is not None:
                msg = f"Feature '{feature}' contains forbidden term '{matched}'"
                raise ValueError(msg)
        return value

    @field_validator("example_synthetic_payload")
    @classmethod
    def validate_payload(cls, value: dict[str, str]) -> dict[str, str]:
        for key, payload_value in value.items():
            for candidate in (key, payload_value):
                matched = contains_forbidden_term(candidate)
                if matched is not None:
                    msg = f"Payload contains forbidden term '{matched}'"
                    raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_confidence_range(self) -> TaxonomyEventDefinition:
        low, high = self.expected_confidence_range
        if low > high:
            msg = "expected_confidence_range lower bound must not exceed upper bound"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def reject_identity_and_biometric_requirements(self) -> TaxonomyEventDefinition:
        if self.requires_identity:
            msg = "DUALEXIS taxonomy events must not require identity"
            raise ValueError(msg)
        if self.requires_biometric:
            msg = "DUALEXIS taxonomy events must not require biometric information"
            raise ValueError(msg)
        return self


def _flow_severity() -> SeverityMapping:
    return SeverityMapping(
        bands=(
            SeverityBand(min_confidence=0.0, max_confidence=0.49, severity=SeverityLevel.LOW),
            SeverityBand(min_confidence=0.5, max_confidence=0.74, severity=SeverityLevel.MEDIUM),
            SeverityBand(min_confidence=0.75, max_confidence=1.0, severity=SeverityLevel.HIGH),
        )
    )


def _access_severity() -> SeverityMapping:
    return SeverityMapping(
        bands=(
            SeverityBand(min_confidence=0.0, max_confidence=0.59, severity=SeverityLevel.LOW),
            SeverityBand(min_confidence=0.6, max_confidence=0.79, severity=SeverityLevel.MEDIUM),
            SeverityBand(min_confidence=0.8, max_confidence=1.0, severity=SeverityLevel.HIGH),
        )
    )


def _audio_severity() -> SeverityMapping:
    return SeverityMapping(
        bands=(
            SeverityBand(min_confidence=0.0, max_confidence=0.54, severity=SeverityLevel.LOW),
            SeverityBand(min_confidence=0.55, max_confidence=0.79, severity=SeverityLevel.MEDIUM),
            SeverityBand(min_confidence=0.8, max_confidence=1.0, severity=SeverityLevel.HIGH),
        )
    )


def _safety_severity() -> SeverityMapping:
    return SeverityMapping(
        bands=(
            SeverityBand(min_confidence=0.0, max_confidence=0.64, severity=SeverityLevel.MEDIUM),
            SeverityBand(min_confidence=0.65, max_confidence=0.84, severity=SeverityLevel.HIGH),
            SeverityBand(min_confidence=0.85, max_confidence=1.0, severity=SeverityLevel.CRITICAL),
        )
    )


def _multimodal_severity() -> SeverityMapping:
    return SeverityMapping(
        bands=(
            SeverityBand(min_confidence=0.0, max_confidence=0.49, severity=SeverityLevel.LOW),
            SeverityBand(min_confidence=0.5, max_confidence=0.74, severity=SeverityLevel.MEDIUM),
            SeverityBand(min_confidence=0.75, max_confidence=1.0, severity=SeverityLevel.HIGH),
        )
    )


def _build_event_taxonomy() -> dict[TaxonomyEventType, TaxonomyEventDefinition]:
    """Construct the full taxonomy registry."""
    definitions: list[TaxonomyEventDefinition] = [
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.NORMAL_FLOW,
            category=EventCategory.FLOW,
            description=(
                "Aggregate pedestrian movement within expected density and velocity bounds "
                "for the zone; aggregate motion only, no occupant-level tracks."
            ),
            input_modalities=(InputModality.VIDEO, InputModality.SENSOR),
            measurable_features=(
                "occupancy_estimate",
                "mean_velocity",
                "flow_direction_entropy",
            ),
            expected_confidence_range=(0.55, 0.95),
            severity_mapping=_flow_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="flow_stability_index",
            example_synthetic_payload={
                "zone_id": "hallway-a",
                "occupancy_estimate": "18",
                "mean_velocity": "0.42",
                "flow_direction_entropy": "0.31",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.CROWD_ACCELERATION,
            category=EventCategory.FLOW,
            description=(
                "Zone-level surge in aggregate motion or density velocity indicating "
                "accelerating crowd movement using zone-level motion descriptors only."
            ),
            input_modalities=(InputModality.VIDEO, InputModality.SENSOR),
            measurable_features=(
                "density_velocity_delta",
                "occupancy_delta",
                "motion_magnitude",
            ),
            expected_confidence_range=(0.45, 0.92),
            severity_mapping=_flow_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="crowd_velocity_delta",
            example_synthetic_payload={
                "zone_id": "cafeteria",
                "density_velocity_delta": "0.28",
                "occupancy_delta": "12",
                "motion_magnitude": "0.61",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.CROWD_CONGESTION,
            category=EventCategory.FLOW,
            description=(
                "Sustained high occupancy with reduced throughput suggesting congestion "
                "in a confined zone."
            ),
            input_modalities=(InputModality.VIDEO, InputModality.SENSOR),
            measurable_features=(
                "occupancy_ratio",
                "throughput_rate",
                "dwell_time_estimate",
            ),
            expected_confidence_range=(0.5, 0.9),
            severity_mapping=_flow_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="congestion_density_score",
            example_synthetic_payload={
                "zone_id": "stairwell-b",
                "occupancy_ratio": "0.88",
                "throughput_rate": "0.12",
                "dwell_time_estimate": "45",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.COUNTERFLOW,
            category=EventCategory.FLOW,
            description=(
                "Opposing aggregate movement vectors detected within the same zone, "
                "indicating bidirectional flow conflict."
            ),
            input_modalities=(InputModality.VIDEO,),
            measurable_features=(
                "counterflow_ratio",
                "vector_opposition_score",
                "lane_occupancy_balance",
            ),
            expected_confidence_range=(0.4, 0.88),
            severity_mapping=_flow_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="counterflow_ratio",
            example_synthetic_payload={
                "zone_id": "corridor-main",
                "counterflow_ratio": "0.47",
                "vector_opposition_score": "0.63",
                "lane_occupancy_balance": "0.52",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.SUDDEN_DISPERSION,
            category=EventCategory.FLOW,
            description=(
                "Rapid decrease in zone occupancy coupled with elevated exit-directed "
                "motion suggesting sudden dispersal."
            ),
            input_modalities=(InputModality.VIDEO, InputModality.SENSOR),
            measurable_features=(
                "occupancy_drop_rate",
                "exit_directed_motion_ratio",
                "dispersion_duration_seconds",
            ),
            expected_confidence_range=(0.45, 0.9),
            severity_mapping=_flow_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="dispersion_rate",
            example_synthetic_payload={
                "zone_id": "lobby",
                "occupancy_drop_rate": "0.55",
                "exit_directed_motion_ratio": "0.71",
                "dispersion_duration_seconds": "8",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.EXIT_BLOCKAGE,
            category=EventCategory.ACCESS_AND_ROUTE,
            description=(
                "Exit route or egress point appears obstructed based on door sensors "
                "and aggregate flow stall patterns."
            ),
            input_modalities=(InputModality.SENSOR, InputModality.VIDEO),
            measurable_features=(
                "door_state",
                "egress_flow_rate",
                "obstruction_score",
            ),
            expected_confidence_range=(0.5, 0.93),
            severity_mapping=_access_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="exit_clearance_score",
            example_synthetic_payload={
                "zone_id": "exit-c",
                "door_state": "blocked",
                "egress_flow_rate": "0.02",
                "obstruction_score": "0.84",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.ROUTE_UNAVAILABLE,
            category=EventCategory.ACCESS_AND_ROUTE,
            description=(
                "Planned evacuation or circulation route is unavailable due to barrier, "
                "closure, or sensor-detected obstruction."
            ),
            input_modalities=(InputModality.SENSOR, InputModality.VIDEO),
            measurable_features=(
                "route_id",
                "barrier_detected",
                "alternative_route_count",
            ),
            expected_confidence_range=(0.55, 0.91),
            severity_mapping=_access_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="route_availability_score",
            example_synthetic_payload={
                "zone_id": "route-north",
                "route_id": "evac-north-1",
                "barrier_detected": "true",
                "alternative_route_count": "2",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.DOOR_FORCED,
            category=EventCategory.ACCESS_AND_ROUTE,
            description=(
                "Door or access point forced open outside expected schedule based on "
                "sensor anomalies; no occupant-level attribution."
            ),
            input_modalities=(InputModality.SENSOR, InputModality.AUDIO),
            measurable_features=(
                "door_force_magnitude",
                "open_duration_seconds",
                "schedule_violation_flag",
            ),
            expected_confidence_range=(0.6, 0.95),
            severity_mapping=_access_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="door_force_anomaly_score",
            example_synthetic_payload={
                "zone_id": "service-door-2",
                "door_force_magnitude": "0.78",
                "open_duration_seconds": "14",
                "schedule_violation_flag": "true",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.RESTRICTED_AREA_ENTRY,
            category=EventCategory.ACCESS_AND_ROUTE,
            description=(
                "Aggregate motion or access sensor activity in a restricted zone without "
                "occupant-level attribution or profiling."
            ),
            input_modalities=(InputModality.SENSOR, InputModality.VIDEO),
            measurable_features=(
                "restricted_zone_id",
                "entry_motion_score",
                "authorized_schedule_match",
            ),
            expected_confidence_range=(0.5, 0.9),
            severity_mapping=_access_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="unauthorized_zone_entry_score",
            example_synthetic_payload={
                "zone_id": "restricted-lab",
                "restricted_zone_id": "restricted-lab",
                "entry_motion_score": "0.67",
                "authorized_schedule_match": "false",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.AUDIO_STRESS_SIGNAL,
            category=EventCategory.AUDIO,
            description=(
                "Elevated acoustic stress indicators (volume, spectral energy) in a zone "
                "without utterance fingerprinting or persistent audio retention."
            ),
            input_modalities=(InputModality.AUDIO,),
            measurable_features=(
                "rms_energy",
                "high_frequency_ratio",
                "stress_index",
            ),
            expected_confidence_range=(0.4, 0.88),
            severity_mapping=_audio_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="acoustic_stress_index",
            example_synthetic_payload={
                "zone_id": "cafeteria",
                "rms_energy": "0.72",
                "high_frequency_ratio": "0.41",
                "stress_index": "0.58",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.GLASS_BREAK,
            category=EventCategory.AUDIO,
            description=(
                "Transient high-frequency acoustic signature consistent with glass fracture "
                "localized to a zone."
            ),
            input_modalities=(InputModality.AUDIO, InputModality.SENSOR),
            measurable_features=(
                "transient_peak_frequency_hz",
                "spectral_flatness",
                "glass_break_classifier_score",
            ),
            expected_confidence_range=(0.55, 0.96),
            severity_mapping=_audio_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="glass_break_detection_score",
            example_synthetic_payload={
                "zone_id": "lobby-window",
                "transient_peak_frequency_hz": "4200",
                "spectral_flatness": "0.33",
                "glass_break_classifier_score": "0.89",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.ALARM_DETECTED,
            category=EventCategory.AUDIO,
            description=(
                "Recognized alarm tone or siren pattern in the acoustic environment "
                "without recording persistent raw audio."
            ),
            input_modalities=(InputModality.AUDIO, InputModality.SENSOR),
            measurable_features=(
                "alarm_template_match_score",
                "tone_frequency_hz",
                "duration_seconds",
            ),
            expected_confidence_range=(0.65, 0.98),
            severity_mapping=_audio_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="alarm_match_score",
            example_synthetic_payload={
                "zone_id": "building-wide",
                "alarm_template_match_score": "0.94",
                "tone_frequency_hz": "880",
                "duration_seconds": "3",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.IMPACT_SOUND,
            category=EventCategory.AUDIO,
            description=(
                "Short-duration impact transient detected acoustically or via vibration "
                "sensors; no source attribution inference."
            ),
            input_modalities=(InputModality.AUDIO, InputModality.SENSOR),
            measurable_features=(
                "impact_peak_amplitude",
                "decay_time_ms",
                "vibration_correlation_score",
            ),
            expected_confidence_range=(0.45, 0.9),
            severity_mapping=_audio_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="impact_transient_score",
            example_synthetic_payload={
                "zone_id": "hallway-b",
                "impact_peak_amplitude": "0.81",
                "decay_time_ms": "120",
                "vibration_correlation_score": "0.74",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.VERBAL_HELP_REQUEST,
            category=EventCategory.AUDIO,
            description=(
                "Distress vocalization or help-request phrase class detected at zone level "
                "without utterance-level fingerprinting or diarization."
            ),
            input_modalities=(InputModality.AUDIO,),
            measurable_features=(
                "distress_phrase_match_score",
                "vocalization_energy",
                "phrase_duration_seconds",
            ),
            expected_confidence_range=(0.5, 0.92),
            severity_mapping=_audio_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.HIGH,
            evaluation_metric="distress_vocalization_score",
            example_synthetic_payload={
                "zone_id": "restroom-area",
                "distress_phrase_match_score": "0.76",
                "vocalization_energy": "0.68",
                "phrase_duration_seconds": "2",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.FALL_DETECTED,
            category=EventCategory.SAFETY,
            description=(
                "Posture or motion pattern consistent with a fall event at zone granularity; "
                "aggregate descriptors only, no persistent video storage."
            ),
            input_modalities=(InputModality.VIDEO, InputModality.SENSOR),
            measurable_features=(
                "vertical_velocity_drop",
                "posture_change_score",
                "stillness_duration_seconds",
            ),
            expected_confidence_range=(0.55, 0.94),
            severity_mapping=_safety_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="fall_event_detection_rate",
            example_synthetic_payload={
                "zone_id": "corridor-east",
                "vertical_velocity_drop": "0.79",
                "posture_change_score": "0.85",
                "stillness_duration_seconds": "6",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.PANIC_BUTTON_PRESSED,
            category=EventCategory.SAFETY,
            description=(
                "Manual panic or duress button activation reported by a fixed sensor node "
                "without associating the activation with a specific occupant."
            ),
            input_modalities=(InputModality.SENSOR,),
            measurable_features=(
                "button_id",
                "activation_timestamp",
                "sensor_integrity_score",
            ),
            expected_confidence_range=(0.85, 1.0),
            severity_mapping=_safety_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="panic_button_activation_score",
            example_synthetic_payload={
                "zone_id": "reception",
                "button_id": "panic-reception-01",
                "activation_timestamp": "2026-01-01T12:04:00Z",
                "sensor_integrity_score": "0.99",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.EVACUATION_SIGNAL,
            category=EventCategory.SAFETY,
            description=(
                "Corroborated indicators suggesting an evacuation-relevant condition "
                "across flow, access, and environmental sensors."
            ),
            input_modalities=(
                InputModality.VIDEO,
                InputModality.AUDIO,
                InputModality.SENSOR,
            ),
            measurable_features=(
                "evacuation_corroboration_score",
                "exit_utilization_rate",
                "announcement_detected",
            ),
            expected_confidence_range=(0.6, 0.95),
            severity_mapping=_safety_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="evacuation_corroboration_score",
            example_synthetic_payload={
                "zone_id": "building-wide",
                "evacuation_corroboration_score": "0.82",
                "exit_utilization_rate": "0.91",
                "announcement_detected": "true",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.FIRE_OR_SMOKE_SIGNAL,
            category=EventCategory.SAFETY,
            description=(
                "Environmental hazard indicators (smoke particulate, heat, alarm correlation) "
                "localized to a zone without forensic media retention."
            ),
            input_modalities=(InputModality.SENSOR, InputModality.AUDIO),
            measurable_features=(
                "smoke_density_ppm",
                "heat_delta_celsius",
                "hazard_correlation_score",
            ),
            expected_confidence_range=(0.7, 0.99),
            severity_mapping=_safety_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="environmental_hazard_score",
            example_synthetic_payload={
                "zone_id": "kitchen-adjacent",
                "smoke_density_ppm": "42",
                "heat_delta_celsius": "8.5",
                "hazard_correlation_score": "0.93",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.MULTIMODAL_CONFIRMATION,
            category=EventCategory.MULTIMODAL,
            description=(
                "Independent modalities agree on the same semantic hypothesis, increasing "
                "confidence without occupant-level linkage."
            ),
            input_modalities=(
                InputModality.VIDEO,
                InputModality.AUDIO,
                InputModality.SENSOR,
            ),
            measurable_features=(
                "cross_modal_agreement_score",
                "modality_count",
                "label_consistency_ratio",
            ),
            expected_confidence_range=(0.55, 0.95),
            severity_mapping=_multimodal_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="cross_modal_agreement_rate",
            example_synthetic_payload={
                "zone_id": "exit-c",
                "cross_modal_agreement_score": "0.87",
                "modality_count": "3",
                "label_consistency_ratio": "0.92",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.MULTIMODAL_CONFLICT,
            category=EventCategory.MULTIMODAL,
            description=(
                "Modalities produce divergent semantic labels for the same zone and window, "
                "requiring conservative human review."
            ),
            input_modalities=(
                InputModality.VIDEO,
                InputModality.AUDIO,
                InputModality.SENSOR,
            ),
            measurable_features=(
                "cross_modal_conflict_score",
                "dominant_label_margin",
                "modality_disagreement_count",
            ),
            expected_confidence_range=(0.4, 0.85),
            severity_mapping=_multimodal_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="cross_modal_conflict_rate",
            example_synthetic_payload={
                "zone_id": "cafeteria",
                "cross_modal_conflict_score": "0.71",
                "dominant_label_margin": "0.09",
                "modality_disagreement_count": "2",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.RISK_ESCALATION,
            category=EventCategory.MULTIMODAL,
            description=(
                "Temporal fusion indicates increasing risk across consecutive semantic events "
                "within a zone or adjacent zones."
            ),
            input_modalities=(
                InputModality.VIDEO,
                InputModality.AUDIO,
                InputModality.SENSOR,
            ),
            measurable_features=(
                "risk_escalation_index",
                "severity_delta",
                "event_chain_length",
            ),
            expected_confidence_range=(0.5, 0.9),
            severity_mapping=_multimodal_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.MEDIUM,
            evaluation_metric="risk_escalation_index",
            example_synthetic_payload={
                "zone_id": "stairwell-a",
                "risk_escalation_index": "0.68",
                "severity_delta": "0.25",
                "event_chain_length": "4",
            },
        ),
        TaxonomyEventDefinition(
            event_type=TaxonomyEventType.RISK_DEESCALATION,
            category=EventCategory.MULTIMODAL,
            description=(
                "Temporal fusion indicates decreasing risk following mitigation or natural "
                "resolution of prior semantic events."
            ),
            input_modalities=(
                InputModality.VIDEO,
                InputModality.AUDIO,
                InputModality.SENSOR,
            ),
            measurable_features=(
                "risk_deescalation_index",
                "severity_delta",
                "resolution_duration_seconds",
            ),
            expected_confidence_range=(0.45, 0.88),
            severity_mapping=_multimodal_severity(),
            privacy_risk_level=TaxonomyPrivacyRisk.LOW,
            evaluation_metric="risk_deescalation_index",
            example_synthetic_payload={
                "zone_id": "lobby",
                "risk_deescalation_index": "0.74",
                "severity_delta": "-0.30",
                "resolution_duration_seconds": "120",
            },
        ),
    ]
    return {definition.event_type: definition for definition in definitions}


EVENT_TAXONOMY: dict[TaxonomyEventType, TaxonomyEventDefinition] = _build_event_taxonomy()


def get_event_definition(event_type: TaxonomyEventType) -> TaxonomyEventDefinition:
    """Return the formal definition for *event_type*."""
    return EVENT_TAXONOMY[event_type]


def all_event_types() -> tuple[TaxonomyEventType, ...]:
    """Return all taxonomy event types in declaration order."""
    return tuple(TaxonomyEventType)


def events_by_category(category: EventCategory) -> tuple[TaxonomyEventDefinition, ...]:
    """Return event definitions belonging to *category*."""
    return tuple(
        definition for definition in EVENT_TAXONOMY.values() if definition.category == category
    )


def validate_taxonomy_registry() -> None:
    """Raise ``ValueError`` if the taxonomy registry is incomplete or inconsistent."""
    missing = set(TaxonomyEventType) - set(EVENT_TAXONOMY)
    if missing:
        msg = f"Missing taxonomy definitions: {sorted(missing)}"
        raise ValueError(msg)
    extra = set(EVENT_TAXONOMY) - set(TaxonomyEventType)
    if extra:
        msg = f"Unexpected taxonomy keys: {sorted(extra)}"
        raise ValueError(msg)


__all__ = [
    "EVENT_TAXONOMY",
    "EventCategory",
    "InputModality",
    "SeverityBand",
    "SeverityMapping",
    "TaxonomyEventDefinition",
    "TaxonomyEventType",
    "TaxonomyPrivacyRisk",
    "all_event_types",
    "events_by_category",
    "get_event_definition",
    "validate_taxonomy_registry",
]
