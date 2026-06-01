# Local Reasoning Layer (L5)

The Local Reasoning Layer implements a **safety orchestration copilot** that operates exclusively on structured artifacts exported from upstream layers. Raw video, audio payloads, images, biometric features, and personal identities never enter the reasoning context (trust boundary **TB4**).

## Purpose

L5 transforms privacy-validated semantic events and temporal graph context into **advisory recommendations** for human operators. Recommendations are never autonomous enforcement actions.

## Permitted Inputs

The reasoner accepts only:

| Input | Source layer | Description |
|-------|--------------|-------------|
| Semantic events | L3 | Anchor and context `SemanticEvent` records |
| Temporal graph context | L4 | `GraphContext` JSON snapshot (zones, routes, risk states) |
| Active safety constraints | Policy / orchestration | Closed constraint vocabulary |
| Available protocols | Orchestration | Closed operational protocol vocabulary |

## Prohibited Inputs

The reasoner **must never** receive:

- Raw video or audio buffers
- Images or frame payloads
- Biometric features (face embeddings, voiceprints, etc.)
- Personal identities (`person_id`, `student_id`, names, etc.)

Violations raise `PrivacyViolationError` (fail-closed) via `validate_reasoning_payload()`.

## Output Schema

`LocalReasoningOutput` fields:

| Field | Type | Description |
|-------|------|-------------|
| `recommendation` | `str` | Human-readable advisory action summary |
| `rationale` | `str` | Grounded explanation citing structured evidence |
| `confidence` | `float` | Numeric confidence in `[0, 1]` |
| `required_human_review` | `bool` | Whether L6 must queue human review |
| `uncertainty_notes` | `str` | Explicit uncertainty disclosure |
| `cited_event_ids` | `tuple[UUID, ...]` | Source semantic events referenced |

Legacy pipeline integration maps these fields to `ReasoningResponse` (`summary`, `explanation`, `recommended_action`, `requires_human_review`).

## Module Layout

```
dualexis/local_reasoning/
  models.py            # LocalReasoningInput/Output, validation
  interfaces.py        # Reasoner and LocalReasoningService ABCs
  service.py           # DefaultLocalReasoningService
  prompt_templates.py  # Privacy-preserving prompt serialization
  mock_llm.py          # Deterministic MockLLMReasoner (v0.1 default)
```

## Usage

### Structured API (preferred)

```python
from dualexis.local_reasoning import (
    DefaultLocalReasoningService,
    LocalReasoningInput,
)

service = DefaultLocalReasoningService()
output = await service.reason_structured(reasoning_input)
print(output.recommendation, output.cited_event_ids)
```

### Legacy API (pipeline / orchestrator)

```python
from dualexis.local_reasoning import PlaceholderLocalReasoningService
from dualexis.schemas.reasoning import ReasoningRequest

service = PlaceholderLocalReasoningService()
response = await service.reason(request)
```

Both paths delegate to `MockLLMReasoner` until a production local LLM backend is integrated.

## MockLLMReasoner

The reference v0.1 backend is **deterministic** and requires **no external LLM dependencies**:

- Maps anchor event severity to a closed `RecommendedAction` vocabulary
- Cites anchor and context event IDs in every output
- Sets `required_human_review=True` for medium, high, and critical severities
- Builds (but does not transmit) structured prompts via `build_structured_prompt()`

## Privacy Validation

```python
from dualexis.local_reasoning import validate_reasoning_payload

validate_reasoning_payload(reasoning_input.model_dump(mode="json"))
```

Scans serialized input recursively for forbidden media, image, biometric, and identity keys defined in `privacy_runtime` plus L5 image field extensions.

## Integration Points

| Consumer | Interface |
|----------|-----------|
| Pipeline L5 step | `LocalReasoningService.reason(ReasoningRequest)` |
| Orchestrator | Same legacy request/response path |
| Temporal graph | Supplies `GraphContext` via `get_reasoning_context()` |
| L6 orchestration | Consumes `recommended_action` and review flags |

## Configuration

`CopilotConfig` defaults:

- `model_id = "mock-llm-reasoner"`
- `max_context_events = 32`
- `allow_raw_media_prompts = False`

## Testing

```bash
pytest tests/unit/test_local_reasoning.py -v
```

Coverage includes:

- Raw media rejection
- Identity field rejection
- High-risk human review requirement
- Deterministic mock output
- Event ID citation in recommendations

## Related Documentation

- [Temporal graph](temporal_graph.md) — L4 context export
- [Privacy model](privacy.md) — TB4 egress rules
- [Pipeline](pipeline.md) — end-to-end L5 invocation
