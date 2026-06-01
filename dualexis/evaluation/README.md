# Evaluation Layer

Pre-registered metrics and benchmark protocol support.

## Purpose

Register DUALEXIS evaluation metrics and phases **without fabricating results**. Provides the configuration surface for Q1 reproducibility (privacy audit, functional benchmarks, field pilot).

## Inputs

- `MetricTarget` definitions (YAML/manifest imports planned)
- Scenario IDs and ground-truth labels from the simulation layer
- Future: benchmark runner outputs (latency, F1, PDE)

## Outputs

- `registered_metrics()` — frozen metric catalog
- `run_evaluation()` — reproducible scaffold reports (`EvaluationReport`)
- `is_implemented()` — partial runner availability flags

## Privacy constraints

- Metrics include raw media retention and personal data exposure scores
- No real occupant video or identity-labeled datasets in default targets
- Evaluation artifacts remain metadata-only until ethics-approved collection

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `EvaluationService` ABC |
| `models.py` | `EvaluationMetric`, `MetricTarget`, phases |
| `metrics.py` | Metric computations |
| `baselines.py` | Pluggable baseline implementations |
| `report.py` | `EvaluationReport` generation |
| `service.py` | `PlaceholderEvaluationService` |

## Usage

```python
from dualexis.evaluation import run_evaluation

report = run_evaluation("exit_blockage", "rule_based", seed=42)
print(report.metrics.false_positive_rate)
```

CLI:

```bash
dualexis evaluate --scenario exit_blockage --baseline rule_based --seed 42
```
