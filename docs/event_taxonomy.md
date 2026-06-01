# DUALEXIS Event Taxonomy

This document defines the **formal DUALEXIS event taxonomy**: zone-scoped, identity-free
semantic categories used by the Semantic Event Layer (L3), simulation harness, evaluation
scaffold, and end-to-end pipeline.

The canonical machine-readable registry lives in `dualexis/semantic_events/taxonomy.py`.

## Design Principles

- **Events, not identities** — no event type requires occupant identification or profiling.
- **No biometrics** — facial recognition, voice-print matching, and similar signals are excluded.
- **Zone-scoped semantics** — every event is anchored to a `zone_id` and aggregate features.
- **Ephemeral perception** — example payloads contain measurable features only; no raw media refs.

## Category Overview

| Category | Event types | Primary modalities |
| -------- | ----------- | ------------------ |
| Flow events | 5 | video, sensor |
| Access and route events | 4 | sensor, video, audio |
| Audio events | 5 | audio, sensor |
| Safety events | 4 | video, audio, sensor |
| Multimodal events | 4 | video, audio, sensor |

## Per-Event Specification Fields

Each `TaxonomyEventDefinition` includes:

| Field | Description |
| ----- | ----------- |
| `description` | Human-readable semantics (identity-free) |
| `input_modalities` | Contributing perception channels |
| `measurable_features` | Aggregate, zone-level feature names |
| `expected_confidence_range` | Typical detector confidence interval |
| `severity_mapping` | Confidence-to-severity translation bands |
| `privacy_risk_level` | Mishandling risk (`low`, `medium`, `high`) |
| `evaluation_metric` | Pre-registered benchmark metric name |
| `example_synthetic_payload` | Simulation-friendly feature dictionary |

---

## 1. Flow Events

### `normal_flow`

| Attribute | Value |
| --------- | ----- |
| Description | Aggregate pedestrian movement within expected density and velocity bounds |
| Modalities | video, sensor |
| Features | `occupancy_estimate`, `mean_velocity`, `flow_direction_entropy` |
| Confidence | 0.55 – 0.95 |
| Severity | LOW → MEDIUM → HIGH by confidence band |
| Privacy risk | low |
| Metric | `flow_stability_index` |

Example payload:

```json
{
  "zone_id": "hallway-a",
  "occupancy_estimate": "18",
  "mean_velocity": "0.42",
  "flow_direction_entropy": "0.31"
}
```

### `crowd_acceleration`

| Attribute | Value |
| --------- | ----- |
| Description | Zone-level surge in aggregate motion or density velocity |
| Modalities | video, sensor |
| Features | `density_velocity_delta`, `occupancy_delta`, `motion_magnitude` |
| Confidence | 0.45 – 0.92 |
| Privacy risk | low |
| Metric | `crowd_velocity_delta` |

### `crowd_congestion`

| Attribute | Value |
| --------- | ----- |
| Description | Sustained high occupancy with reduced throughput |
| Modalities | video, sensor |
| Features | `occupancy_ratio`, `throughput_rate`, `dwell_time_estimate` |
| Confidence | 0.5 – 0.9 |
| Metric | `congestion_density_score` |

### `counterflow`

| Attribute | Value |
| --------- | ----- |
| Description | Opposing aggregate movement vectors in the same zone |
| Modalities | video |
| Features | `counterflow_ratio`, `vector_opposition_score`, `lane_occupancy_balance` |
| Confidence | 0.4 – 0.88 |
| Metric | `counterflow_ratio` |

### `sudden_dispersion`

| Attribute | Value |
| --------- | ----- |
| Description | Rapid occupancy drop with exit-directed motion |
| Modalities | video, sensor |
| Features | `occupancy_drop_rate`, `exit_directed_motion_ratio`, `dispersion_duration_seconds` |
| Confidence | 0.45 – 0.9 |
| Privacy risk | medium |
| Metric | `dispersion_rate` |

---

## 2. Access and Route Events

### `exit_blockage`

| Attribute | Value |
| --------- | ----- |
| Description | Egress point obstructed based on sensors and flow stall patterns |
| Modalities | sensor, video |
| Features | `door_state`, `egress_flow_rate`, `obstruction_score` |
| Confidence | 0.5 – 0.93 |
| Metric | `exit_clearance_score` |

### `route_unavailable`

| Attribute | Value |
| --------- | ----- |
| Description | Planned route unavailable due to barrier or closure |
| Modalities | sensor, video |
| Features | `route_id`, `barrier_detected`, `alternative_route_count` |
| Metric | `route_availability_score` |

### `door_forced`

| Attribute | Value |
| --------- | ----- |
| Description | Door forced open outside expected schedule (no occupant ID) |
| Modalities | sensor, audio |
| Features | `door_force_magnitude`, `open_duration_seconds`, `schedule_violation_flag` |
| Privacy risk | medium |
| Metric | `door_force_anomaly_score` |

### `restricted_area_entry`

| Attribute | Value |
| --------- | ----- |
| Description | Aggregate motion in a restricted zone without identification |
| Modalities | sensor, video |
| Features | `restricted_zone_id`, `entry_motion_score`, `authorized_schedule_match` |
| Privacy risk | medium |
| Metric | `unauthorized_zone_entry_score` |

---

## 3. Audio Events

All audio events use **ephemeral acoustic features** — no raw audio storage or speaker ID.

| Event type | Metric | Privacy risk |
| ---------- | ------ | ------------ |
| `audio_stress_signal` | `acoustic_stress_index` | medium |
| `glass_break` | `glass_break_detection_score` | low |
| `alarm_detected` | `alarm_match_score` | low |
| `impact_sound` | `impact_transient_score` | low |
| `verbal_help_request` | `distress_vocalization_score` | high |

See `taxonomy.py` for full feature lists and example payloads.

---

## 4. Safety Events

| Event type | Modalities | Metric |
| ---------- | ---------- | ------ |
| `fall_detected` | video, sensor | `fall_event_detection_rate` |
| `panic_button_pressed` | sensor | `panic_button_activation_score` |
| `evacuation_signal` | video, audio, sensor | `evacuation_corroboration_score` |
| `fire_or_smoke_signal` | sensor, audio | `environmental_hazard_score` |

Safety events use elevated severity bands (MEDIUM → HIGH → CRITICAL).

---

## 5. Multimodal Events

| Event type | Description | Metric |
| ---------- | ----------- | ------ |
| `multimodal_confirmation` | Modalities agree on the same hypothesis | `cross_modal_agreement_rate` |
| `multimodal_conflict` | Modalities produce divergent labels | `cross_modal_conflict_rate` |
| `risk_escalation` | Increasing risk across temporal event chain | `risk_escalation_index` |
| `risk_deescalation` | Decreasing risk after resolution | `risk_deescalation_index` |

---

## Python API

```python
from dualexis.semantic_events.taxonomy import (
    EVENT_TAXONOMY,
    TaxonomyEventType,
    get_event_definition,
    validate_taxonomy_registry,
)

validate_taxonomy_registry()
definition = get_event_definition(TaxonomyEventType.EXIT_BLOCKAGE)
print(definition.evaluation_metric, definition.input_modalities)
```

## Relationship to `EventType`

The legacy `dualexis.semantic_events.models.EventType` enumeration remains a **runtime subset**
used by simulation and pipeline v0.1. The formal taxonomy superset is authoritative for
benchmark design and paper pre-registration.

## Related Documentation

- [Framework](framework.md)
- [Simulation](simulation.md)
- [Evaluation](evaluation.md)
- LaTeX: `paper/sections/event_taxonomy.tex`
