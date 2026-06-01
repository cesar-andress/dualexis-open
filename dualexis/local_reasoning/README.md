# L5: Local Reasoning Layer

Structured-event copilot for advisory safety reasoning.

## Purpose

Produce `ReasoningResponse` summaries and recommended **advisory** actions from structured event subgraphs. Never consumes raw video, audio bytes, or identity fields.

## Inputs

- `ReasoningRequest` — anchor event, temporal context events, optional operator prompt
- `CopilotConfig` — placeholder model ID and context limits

## Outputs

- `ReasoningResponse` — summary, explanation, confidence, recommended action
- `requires_human_review` flag for high-risk patterns

## Privacy constraints

- Grounding limited to input event subgraph fields
- `allow_raw_media_prompts` must remain `False` in production configs
- No biometric or student profiling outputs
- Recommendations are non-punitive and require human approval for escalation

## Future implementation plan

- Local LLM backend (llama.cpp / vLLM) with subgraph-only prompts
- Grounding accuracy evaluation against pre-registered QA sets
- Forbidden-term rate monitoring for identity hallucinations
- MR/voice interfaces for frontline staff (hands-free, event-grounded)

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `LocalReasoningService` ABC |
| `models.py` | Reasoning I/O re-exports + `CopilotConfig` |
| `service.py` | `PlaceholderLocalReasoningService` |

## Usage

```python
from dualexis.local_reasoning import PlaceholderLocalReasoningService

copilot = PlaceholderLocalReasoningService()
response = await copilot.reason(request)
```
