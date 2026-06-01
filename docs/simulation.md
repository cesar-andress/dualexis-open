# DUALEXIS Simulation Environment

The DUALEXIS simulation package provides a **reproducible, privacy-safe** confined-space benchmark environment. It models zones, exits, and anonymous flow entities (not personal identities), emits synthetic **`SemanticEvent`** records, and attaches ground-truth scenario labels for evaluation.

No real personal data, raw video, raw audio, or biometrics are used.

## Architecture

| Module | Role |
| ------ | ---- |
| `scenario.py` | Scenario definitions, resolution, and parameters |
| `world.py` | Confined-space graph \(G=(V,E)\), zones, exits, flow entities |
| `event_generator.py` | Synthetic `SemanticEvent` generation from world metrics |
| `ground_truth.py` | Per-tick and aggregate scenario labels |
| `runner.py` | Deterministic tick loop (`random.Random(seed)`) |

## Built-in scenarios

| ID | Ground-truth label | Description |
| -- | ------------------ | ----------- |
| `normal_flow` | `normal_operations` | Baseline anonymous flow |
| `crowd_acceleration` | `crowd_density_elevated` | Rising cafeteria density |
| `exit_blockage` | `exit_blockage` | Reduced exit throughput |
| `audio_stress_signal` | `acoustic_stress` | Synthetic acoustic stress (no raw audio) |
| `multimodal_conflict` | `multimodal_conflict` | Conflicting synthetic modality descriptors |
| `evacuation_recommendation` | `evacuation_review` | Multi-zone stress pattern |

## Quick start

```python
from dualexis.simulation import run_scenario

result = run_scenario("crowd_acceleration", seed=42)
for event in result.events:
    print(event.timestamp, event.zone_id, event.metadata["category"])
print(result.ground_truth.primary_label)
```

CLI:

```bash
dualexis simulate --scenario normal_flow --seed 42
dualexis simulate --scenario exit_blockage --seed 42 --json
```

Example script:

```bash
uv run python examples/simulation_basic/run_simulation.py --scenario exit_blockage --seed 7
```

## Reproducibility

- Fixed scenario definitions in `SCENARIO_DEFINITIONS`
- Seeded pseudo-random noise in world dynamics (`SimulationRunner.seed`)
- Fixed simulation clock anchor in `SyntheticEventGenerator`
- Deterministic `uuid5` event identifiers
- Same seed produces identical event JSON (see `tests/unit/test_simulation.py`)

## Privacy constraints

The simulator:

- Uses **anonymous flow entities** (`flow-{zone_id}`), not person IDs
- Emits **semantic events only** — no raw media bytes, frames, or `payload_ref`
- Sets `EventSource.SIMULATOR` and `PrivacyLevel.SEMANTIC_ONLY`
- Never produces biometric or identity-linked fields

## Integration with evaluation

Phase 2 benchmarks (see `paper/sections/evaluation_plan.tex`) will consume:

1. Synthetic `SemanticEvent` streams from `run_scenario(name, seed=...)`
2. `ScenarioGroundTruth` labels for fusion precision/recall
3. Confined-space topology from `build_default_world()` for graph-layer tests

## Legacy API

`DefaultSimulationService.generate_batch()` remains for lightweight ephemeral frame-batch tests using `SimulationScenario` (hallway acoustic, cafeteria crowd, etc.). The reproducible scenario runner emits semantic events only.

```python
from dualexis.simulation import DefaultSimulationService, SimulationScenario

batch = DefaultSimulationService().generate_batch(
    SimulationScenario.MULTIMODAL_CORRELATED,
    node_id="sim-edge-001",
    zone_id="hallway-a",
)
```
