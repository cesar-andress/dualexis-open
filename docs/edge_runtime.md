# DUALEXIS Edge Runtime

The **edge runtime** (`dualexis/edge_runtime/`) is the first in-process abstraction for
deploying DUALEXIS capture-adjacent nodes. It models an edge node lifecycle, health
reporting, optional GPU metadata, and **privacy-gated semantic event emission** —
never raw media by default.

Related: [edge_infrastructure.md](edge_infrastructure.md), [privacy.md](privacy.md),
[framework.md](framework.md).

Publication diagram: [edge deployment architecture](diagrams/edge_deployment_architecture.mmd) · [Markdown embed](diagrams/embeds.md#4-edge-deployment-architecture) · rendered [SVG](diagrams/edge_deployment_architecture.svg)

## Responsibilities

| Concern | Module | Notes |
| ------- | ------ | ----- |
| Node manifest | `models.py`, `service.load_edge_node_config` | YAML → `EdgeNodeConfig` |
| Node lifecycle | `node.py`, `service.py` | Start/stop, emission buffer |
| L1 enforcement | `node.py` | `validate_semantic_event` + egress check before emit |
| Health probes | `health.py` | Process, policy, zones, optional GPU |
| Telemetry | `telemetry.py` | Emission/blocked counters |
| CLI | `dualexis edge …` | Status, health, run-node, emit-synthetic |

## Default manifest

`infrastructure/edge/node.yaml` is the reference edge node configuration used by the CLI.
It declares zones, modalities, privacy policy (`strict-v1`), and forbidden egress fields.

## CLI

```bash
dualexis edge status
dualexis edge health
dualexis edge run-node --config infrastructure/edge/node.yaml
dualexis edge emit-synthetic --scenario exit_blockage --seed 42 --json
```

**Typical workflow:**

1. Start the node (optional for synthetic emission): `dualexis edge run-node`
2. Verify health: `dualexis edge health --json`
3. Emit synthetic semantic events: `dualexis edge emit-synthetic …`

`emit-synthetic` auto-starts the node from `--config` when invoked in a fresh CLI
process (each `dualexis` command is stateless across invocations).

## Privacy guarantees

Before any event crosses the TB3 publication boundary:

1. L1 `validate_semantic_event()` scans the payload for forbidden biometric, identity,
   and media fields.
2. `check_egress()` validates the JSON serialization at TB3.
3. Edge-specific metadata checks reject `raw_video`, `raw_audio`, `image_data`, and
   `payload_ref` keys/values in event metadata.

Raw media persistence remains **disabled by default** (`allow_persistent_media: false`).

## GPU metadata

GPU availability is **optional**. When `nvidia-smi` is present, the runtime records
device name and driver version in status/health JSON. CPU-only hosts report
`gpu.available=false` without error.

## Python API

```python
from dualexis.edge_runtime import load_edge_node_config, run_node, emit_synthetic_events

node = run_node("infrastructure/edge/node.yaml")
batch = emit_synthetic_events("exit_blockage", seed=42)
assert batch.raw_media_blocked is True
assert all(not event.raw_media_persisted for event in batch.emitted_events)
```

## Out of scope (this release)

- Live camera/microphone ingestion
- NATS/MQTT transport wiring (manifest fields only)
- Multimodal fusion (Local Orchestrator L3–L6)

These remain documented in [edge_infrastructure.md](edge_infrastructure.md) and future
edge deployment milestones.
