# DUALEXIS K3s Deployment

Lightweight Kubernetes manifests for multi edge-node on-premises sites.

## Prerequisites

- [K3s](https://k3s.io/) cluster (single or multi-node)
- Container images built from `infrastructure/docker/` Dockerfiles
- Optional: NVIDIA GPU Operator for GPU edge nodes

## Layout

```
k3s/
├── namespace.yaml           # dualexis operational namespace
├── nats/deployment.yaml     # Event bus
├── edge-node/               # Per-site edge deployments
├── orchestrator/            # L3–L6 orchestrator
├── api/                     # REST control plane
└── research-server/         # Optional metrics namespace
```

## Install

```bash
# Build and push images (example — adjust registry)
docker build -f infrastructure/docker/Dockerfile.edge -t dualexis/edge-node:local .
docker build -f infrastructure/docker/Dockerfile.orchestrator -t dualexis/orchestrator:local .
docker build -f infrastructure/docker/Dockerfile.api -t dualexis/api:local .

kubectl apply -f namespace.yaml
kubectl apply -f nats/
kubectl apply -f orchestrator/
kubectl apply -f api/
kubectl apply -f edge-node/

# Optional research aggregation (separate namespace)
kubectl apply -f research-server/
```

## Multi edge-node pattern

Deploy one `edge-node` Deployment per capture zone group, each with a unique `DUALEXIS_NODE_ID` ConfigMap. All edge nodes publish to the shared NATS service; the orchestrator subscribes with a queue group.

## GPU edge nodes

Uncomment the `resources.limits.nvidia.com/gpu` section in `edge-node/deployment.yaml` when GPU Operator is installed.

## Network policy

Production sites should restrict:

- Edge pods: egress to NATS and camera VLAN only
- Orchestrator: ingress from NATS; egress to API and optional research server
- Research server: ingress from orchestrator metrics export only

See [docs/edge_infrastructure.md](../../docs/edge_infrastructure.md).
