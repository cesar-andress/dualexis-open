# L2: Edge Perception Layer

Ephemeral multimodal perception at the edge node.

## Purpose

Transform **short-lived** video, audio, and sensor frames into **zone-level** `PerceptionSignal` records. No identity extraction, no media persistence.

## Inputs

- `PerceptionFrame` — modality, node ID, zone ID, optional ephemeral payload reference (no durable storage)
- Registered `PerceptionPipeline` instances per modality

## Outputs

- `PerceptionSignal` — zone descriptors, activity bands, confidence (no person IDs)
- `PerceptionBatch` — grouped signals for a node/zone batch

## Privacy constraints

- Operates only on ephemeral frames validated by L1
- Outputs zone aggregates, not biometric or identity features
- Pipelines must not emit face embeddings, speaker IDs, or student identifiers

## Future implementation plan

- ONNX/runtime adapters for quantized edge models
- Modality dropout and degraded-mode stubs for robustness benchmarks
- Hardware profile manifests (CPU vs. accelerator) for latency evaluation
- Integration with simulation harness for reproducible perception inputs

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `EdgePerceptionService`, `PerceptionPipeline` ABCs |
| `models.py` | Re-exports perception schemas + `PerceptionBatch` |
| `service.py` | `DefaultEdgePerceptionService`, `create_placeholder_service()` |

## Usage

```python
from dualexis.edge_perception import DefaultEdgePerceptionService, create_placeholder_service

service = create_placeholder_service()
```
