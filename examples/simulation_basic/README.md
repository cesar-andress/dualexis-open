# Reproducible Simulation Examples

This directory contains the first reproducible simulation environment for DUALEXIS.

## Quick start

```bash
uv run python examples/simulation_basic/run_simulation.py
uv run python examples/simulation_basic/run_simulation.py --scenario evacuation_recommendation --seed 7
```

Output is written to `examples/simulation_basic/output.json` (semantic event metadata only).

## Scenarios

| ID | Description |
| -- | ----------- |
| `normal_flow` | Baseline anonymous flow |
| `crowd_acceleration` | Rising cafeteria density |
| `exit_blockage` | Reduced exit throughput |
| `audio_stress_signal` | Synthetic acoustic stress (no raw audio) |
| `multimodal_conflict` | Conflicting synthetic modality descriptors |
| `evacuation_recommendation` | Multi-zone stress pattern |

See [docs/simulation.md](../../docs/simulation.md) for full documentation.
