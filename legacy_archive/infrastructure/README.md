# DUALEXIS Infrastructure

On-premises deployment artifacts for the DUALEXIS edge architecture.

| Directory | Purpose |
| --------- | ------- |
| [`docker/`](docker/) | Docker Compose stack for local development (NATS, edge, orchestrator, API) |
| [`edge/`](edge/) | Edge node configuration, NATS subjects, JSON schema |
| [`k3s/`](k3s/) | Lightweight Kubernetes (K3s) manifests for multi-node sites |

**Default posture:** no cloud dependency. All services run locally unless the optional Central Research Server is explicitly enabled.

Documentation: [docs/edge_infrastructure.md](../docs/edge_infrastructure.md).

Quick start (Docker):

```bash
cd infrastructure/docker
cp .env.example .env
docker compose up -d
```
