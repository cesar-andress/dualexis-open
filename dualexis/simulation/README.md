# Simulation Layer

Reproducible confined-space benchmark environment.

## Purpose

Generate synthetic zone-level scenarios, anonymous flow dynamics, and schema-valid `SafetyEvent` streams with ground-truth labels for evaluation and integration tests. **No real personal data, video, or biometrics.**

## Inputs

- `ScenarioId` — built-in scenario identifier
- Random seed for deterministic replay
- Optional node/location IDs for graph topology

## Outputs

- `SimulationResult` — semantic events, ground truth, world graph
- `SyntheticFrameBatch` — legacy frame batches for pipeline smoke tests
- `ScenarioGroundTruth` — per-tick labels for metric computation

## Privacy constraints

- Flow entities are anonymous (`flow-{zone}`), not person IDs
- No raw media bytes or `payload_ref` in synthetic outputs
- Scenarios model aggregate density/stress only
- Suitable for open-source distribution without consent frameworks

## Future implementation plan

- Benchmark runners feeding L1–L6 pipeline under evaluation protocol
- Additional scenarios (fire alarm, drill vs. incident discrimination)
- Export to `examples/evaluation/` manifests
- Hardware-in-the-loop replay at configurable event rates

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `SimulationService` ABC |
| `models.py` | Scenario batches + layer metadata |
| `service.py` | `DefaultSimulationService` |
| `scenario.py`, `world.py`, `runner.py`, … | Reproducible simulation engine |

See also [docs/simulation.md](../../docs/simulation.md).

## Usage

```python
from dualexis.simulation import ScenarioId, run_scenario

result = run_scenario(ScenarioId.NORMAL_FLOW, seed=42)
```
