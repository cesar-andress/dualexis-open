# DUALEXIS End-to-End Pipeline

The `dualexis.pipeline` package orchestrates the full advisory flow from **synthetic local signals** through L1–L6 modules to evaluation and audit artifacts.

No live camera or microphone ingestion is implemented in this release.

## Architecture

Publication diagram: [end-to-end pipeline](diagrams/end_to_end_pipeline.mmd) · [Markdown embed](diagrams/embeds.md#1-end-to-end-pipeline) · rendered [SVG](diagrams/end_to_end_pipeline.svg)

```
Raw local signals (synthetic)
  -> Edge perception (L2)
  -> Privacy runtime (L1)
  -> Semantic event extraction / fusion (L3)
  -> Temporal knowledge graph (L4)
  -> Local reasoning (L5)
  -> Human-in-the-loop recommendation (L6)
  -> Evaluation + audit
```

## Privacy constraints

The pipeline enforces DUALEXIS invariants:

- No facial recognition or biometric identification
- No student or occupant profiling
- No persistent raw video or raw audio storage (`payload_ref=None`)
- No automated punitive decision-making
- High-risk recommendations require human review

## Models

### `PipelineInput`

| Field | Description |
| ----- | ----------- |
| `source_id` | Synthetic edge node identifier |
| `source_type` | `simulator`, `synthetic_edge`, or `manual_fixture` |
| `timestamp` | Observation time (UTC) |
| `synthetic_payload` | Zone metrics and scenario hints (strings only) |
| `metadata` | Validated key/value tags |

### `PipelineOutput`

| Field | Description |
| ----- | ----------- |
| `normalized_events` | Canonical `SemanticEvent` records |
| `fusion_result` | Multimodal fusion output |
| `graph_updates` | Temporal graph mutations |
| `recommendations` | Domain `OrchestrationRecommendation` items |
| `audit_records` | Append-only `AuditEntry` list |
| `privacy_report` | Retention posture + optional evaluation metrics |

## CLI

```bash
uv run dualexis run-pipeline --scenario exit_blockage --seed 42 --json
```

## Python API

```python
from dualexis.pipeline import run_pipeline

output = run_pipeline("exit_blockage", seed=42)
print(len(output.normalized_events), output.privacy_report.policy_compliant)
```

## Module map

| File | Role |
| ---- | ---- |
| `models.py` | `PipelineInput`, `PipelineOutput`, `PrivacyReport` |
| `interfaces.py` | `PipelineService` ABC |
| `service.py` | `DefaultPipelineService`, `run_pipeline()` |

## Related documentation

- [Framework](framework.md)
- [Simulation](simulation.md)
- [Evaluation](evaluation.md)
