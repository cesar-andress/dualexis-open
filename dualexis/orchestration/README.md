# L6: Human-in-the-Loop Orchestration Layer

End-to-end advisory pipeline composition.

## Purpose

Compose L1–L5 into a single **human-in-the-loop** workflow: ephemeral frames → validated events → temporal graph → copilot advice → publish/audit. Outputs support staff decisions; it does not execute punitive actions.

## Inputs

- `list[PerceptionFrame]` — ephemeral multimodal batch for a zone
- Injected L1–L5 service implementations (privacy, perception, events, graph, reasoning)
- `EventPublisher` and `AuditLogger` ports

## Outputs

- `SafetyEvent` — primary published semantic event for the batch
- Audit entries for perception, fusion, reasoning, and publication phases
- Orchestration metadata enforcing review on elevated severities

## Privacy constraints

- Every stage passes through L1 validators
- No persistent raw media; no biometric or identity fields in published artifacts
- High-severity paths require `HumanReviewStatus.PENDING`
- Recommendations remain advisory (`OrchestrationRecommendation`), not automated enforcement

## Future implementation plan

- Staff workflow API with explicit approve/override endpoints
- Time-to-action and review-compliance metrics (evaluation protocol)
- Multi-zone orchestration policies for confined-space graphs
- Integration tests against full simulation scenario harness

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `OrchestrationService` ABC |
| `models.py` | `OrchestrationPhase`, high-risk severity sets |
| `service.py` | `SafetyOrchestrator` reference pipeline |

## Usage

```python
from dualexis.runtime.in_memory import build_safety_orchestrator

orchestrator = build_safety_orchestrator("edge-001", pipelines)
event = await orchestrator.process_frames(frames, zone_id="hall-a")
```
