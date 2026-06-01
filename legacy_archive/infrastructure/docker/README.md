# DUALEXIS Docker Compose Stack

Local, cloud-independent development stack for the DUALEXIS edge deployment model.

## Services

| Service | Role | Port |
| ------- | ---- | ---- |
| `nats` | Event bus (semantic events) | 4222, 8222 (monitor) |
| `edge-node` | L1 + L2 perception and privacy | — |
| `orchestrator` | L3–L6 fusion, graph, reasoning | — |
| `api` | REST control plane / dashboard backend | 8000 |
| `research-server` | Optional metrics aggregation | 8001 (profile `research`) |

## Quick start

```bash
cp .env.example .env
docker compose up -d
curl http://localhost:8000/health
```

## GPU acceleration (NVIDIA)

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d edge-node
```

Set `NVIDIA_VISIBLE_DEVICES` in `.env` to select GPUs.

## Environment

See `.env.example` for `DUALEXIS_*` variables shared across services.

## Architecture

```
Cameras / sensors → edge-node → NATS → orchestrator → api → staff dashboard
                                      ↓
                              (optional) research-server
```

No raw media leaves `edge-node`. See [docs/edge_infrastructure.md](../../docs/edge_infrastructure.md).
