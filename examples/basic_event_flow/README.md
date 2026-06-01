# Basic Event Flow

This example demonstrates the end-to-end DUALEXIS safety event pipeline:

1. **Perception** — ephemeral frames processed at the edge (video, audio, sensor)
2. **Privacy validation** — signals checked against the strict privacy policy
3. **Fusion** — multimodal signals combined into semantic descriptors
4. **Reasoning** — local LLM placeholder generates explainable decision support
5. **Publication** — structured safety event emitted (no raw media)

## Run

```bash
uv run python examples/basic_event_flow/run.py
```

## What to observe

- Events contain zone-level descriptors only (no identities)
- Audit trail entries are created at each pipeline stage
- Human review is flagged for medium+ severity events

## Privacy note

This example uses placeholder perception pipelines. No real camera or microphone
data is processed. Raw media is never stored or transmitted.
