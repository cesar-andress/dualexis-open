# L3: Semantic Event Layer

Multimodal fusion and canonical safety event materialization.

## Purpose

Fuse validated perception signals into explainable `FusionResult` objects and materialize schema-valid `SafetyEvent` records for downstream graph and reasoning layers.

## Inputs

- `FusionInput` — validated `PerceptionSignal` tuple with weights and window metadata
- Fusion engine configuration (default placeholder engine in v0.1)

## Outputs

- `FusionResult` — fused labels, modality contributions, confidence rationale
- `SafetyEvent` / `FusedEvent` — typed events with descriptors and human-review flags

## Privacy constraints

- Consumes L1-validated signals only
- Events reference zones and semantic categories, not individuals
- Descriptor evidence must not contain raw media or biometric keys
- No automated punitive actions — events are informational inputs to L6

## Future implementation plan

- Learned fusion with calibration on simulation ground truth
- Conflict detection for multimodal disagreement scenarios
- Confidence calibration metrics tied to evaluation protocol
- Optional federated fusion without raw signal exchange

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `SemanticEventService` ABC |
| `models.py` | Domain event re-exports + layer metadata |
| `service.py` | `DefaultSemanticEventService` (wraps placeholder fusion engine) |

## Usage

```python
from dualexis.semantic_events import DefaultSemanticEventService

events = DefaultSemanticEventService()
fusion = await events.fuse_signals(fusion_input)
```
