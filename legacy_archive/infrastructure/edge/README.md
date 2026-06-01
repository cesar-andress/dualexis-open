# Edge Node Configuration

Reference configuration for DUALEXIS Edge Nodes deployed at capture boundaries.

## Role summary

| Layer | Function |
| ----- | -------- |
| L2 | Ephemeral perception (video, audio, sensor) |
| L1 | Privacy runtime enforcement before egress |
| Bus | Publish `SemanticEvent` JSON to NATS/MQTT |

Edge nodes **do not** run fusion, graph updates, or LLM reasoning.

## Files

| File | Purpose |
| ---- | ------- |
| `edge-node.example.yaml` | Node manifest (zones, modalities, TTL) |
| `nats-subjects.yaml` | Event bus subject namespace |
| `semantic-event.schema.json` | Wire-format JSON Schema |

## Example deployment

```yaml
# edge-node.example.yaml (excerpt)
node_id: edge-hallway-a
site_id: school-west-01
zones:
  - hallway-a
  - hallway-b
modalities:
  - video
  - audio
nats:
  url: nats://nats.local:4222
  publish_subject: dualexis.events.school-west-01.{zone_id}
privacy:
  edge_buffer_ttl_seconds: 30
  allow_persistent_media: false
```

## Hardware notes

- **CPU-only:** suitable for sensor-heavy or audio-only nodes
- **GPU (NVIDIA):** recommended for video perception; use `docker-compose.gpu.yml` or K3s GPU resource limits

See [docs/edge_infrastructure.md](../../docs/edge_infrastructure.md).
