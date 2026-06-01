# DUALEXIS Evaluation Protocol

This document specifies the **Q1-oriented evaluation methodology** for DUALEXIS. It defines metrics, experimental protocols, baselines, experimental setup, and execution phases. **No results are reported here** — only pre-registered definitions and the reproducible evaluation scaffold.

Formal LaTeX definitions: `paper/sections/metrics.tex` and `paper/sections/evaluation_plan.tex`.
Threat model: `docs/threat_model.md` and `paper/sections/privacy_threats_governance.tex`.

Publication diagram: [experimental evaluation workflow](diagrams/experimental_evaluation_workflow.mmd) · [Markdown embed](diagrams/embeds.md#6-experimental-evaluation-workflow) · rendered [SVG](diagrams/experimental_evaluation_workflow.svg)

## Design principles

1. **Pre-registration** — metrics, protocols, baselines, and scenario sets frozen before experiments.
2. **Reproducibility** — seeded simulation (`dualexis/simulation/`), deterministic protocol executors, lockfiles.
3. **No fabricated results** — placeholder tables remain `TBD` until ethics-approved collection.
4. **Privacy-by-design** — privacy metrics computed from structured outputs only (no raw media).

## Experimental battery (implemented)

A reproducible **experimental battery** runs the full scaffold pipeline for
pre-registered YAML configs under `experiments/configs/`:

| Stage | Module |
| ----- | ------ |
| Synthetic simulation | `dualexis/simulation/` |
| Pipeline execution | `dualexis/pipeline/` |
| Metric collection | `dualexis/evaluation/`, `dualexis/measurement/` |
| Privacy validation | `dualexis/privacy_runtime/` |
| Robustness probes | `dualexis/measurement/robustness.py` |
| Report generation | `dualexis/experiments/runner.py` |

CLI:

```bash
dualexis experiment run --config experiments/configs/exit_blockage.yaml
dualexis experiment run-all --output results/experiments/
dualexis experiment run-multiseed --config-dir experiments/configs/ --seeds 1,2,3,4,5,10,20,42,100,500 --output results/experiments_multiseed/
dualexis experiment report --input results/experiments/ --format markdown
dualexis experiment paper-table --input results/experiments/ --output paper/tables/results.tex
```

Batch script:

```bash
uv run python experiments/run_all.py --output results/experiments/
```

**Important:** Battery outputs report measured scaffold values only. Markdown and
LaTeX artifacts include an explicit disclaimer; no empirical conclusions are generated.

### Multi-seed execution

Run every config for multiple seeds and compute descriptive aggregates (mean, sample
standard deviation, min, max). **No automatic significance testing** is performed.

```bash
dualexis experiment run-multiseed \
  --config-dir experiments/configs/ \
  --seeds 1,2,3,4,5,10,20,42,100,500 \
  --output results/experiments_multiseed/
```

Outputs under `results/experiments_multiseed/`:

| Artifact | Description |
| -------- | ----------- |
| `runs/<experiment>_seed_<n>.json` | Per-run battery JSON |
| `multiseed_summary.json` | Full report bundle |
| `aggregates.json` | Descriptive statistics per experiment |
| `multiseed_report.md` | Markdown summary |
| `multiseed_results.tex` | LaTeX table scaffold |

See `paper/sections/results_scaffold.tex` for interpretation guardrails.

Legacy single-protocol CLI:

```bash
dualexis experiment protocol --scenario exit_blockage --protocol dualexis_full_pipeline --seed 42
```

## External dataset adapters

Annotation-only adapters convert local metadata to `SemanticEvent` records without
downloading datasets or loading raw media. See `docs/datasets.md` and
`dualexis/datasets/`.

## Experimental protocols (implemented)

Four Q1-oriented protocols are registered in `dualexis/evaluation/protocol.py`:

| Protocol ID | Description |
| ----------- | ----------- |
| `single_modality_baseline` | B1-style isolated single-modality alerting |
| `rule_based_fusion_baseline` | B2-style threshold fusion without graph or LLM |
| `semantic_graph_orchestration` | Semantic events + L4 temporal graph ingestion |
| `dualexis_full_pipeline` | Full six-layer DUALEXIS stack (L1--L6) |

CLI:

```bash
dualexis experiment protocol --scenario exit_blockage --protocol dualexis_full_pipeline --seed 42
dualexis experiment protocol --scenario crowd_acceleration --protocol semantic_graph_orchestration --seed 42 --json
```

Legacy baseline CLI (still supported):

```bash
dualexis evaluate --scenario exit_blockage --baseline rule_based --seed 42
```

Python API:

```python
from dualexis.evaluation import run_experiment

report = run_experiment("exit_blockage", "dualexis_full_pipeline", seed=42)
print(report.metrics.event_detection_accuracy)
print(report.metrics.privacy_violation_count)
```

## Module layout

| Module | Role |
| ------ | ---- |
| `dualexis/evaluation/protocol.py` | Protocol registry and executors |
| `dualexis/evaluation/experiment.py` | `run_experiment()` orchestration |
| `dualexis/evaluation/results.py` | `ExperimentReport` and `ExperimentMetrics` |
| `dualexis/evaluation/metrics.py` | Metric computations |
| `dualexis/evaluation/baselines.py` | Legacy baseline implementations |
| `dualexis/evaluation/report.py` | Legacy `EvaluationReport` for baselines |

## Pre-registered experiment metrics

| Metric | Description |
| ------ | ----------- |
| `end_to_end_latency_ms` | Seed-stable scaffold latency for full protocol execution |
| `event_detection_accuracy` | Fraction of ground-truth labels matched by predictions |
| `false_positive_rate` | Unmatched predictions / total predictions |
| `false_negative_rate` | Unmatched ground-truth labels / total labels |
| `time_to_recommendation_ms` | Time until actionable recommendation (scaffold) |
| `explanation_completeness_score` | Fraction of events with zone, explanation, and category |
| `human_review_compliance_rate` | High-severity review compliance placeholder |
| `raw_data_retention_score` | 1.0 when no raw media persists (target) |
| `personal_data_exposure_score` | Lower is better; 0.0 = no observed exposure |
| `privacy_violation_count` | Count of privacy violations in protocol output |
| `graph_update_latency_ms` | L4 graph ingestion latency (scaffold) |

Privacy metrics (`raw_data_retention_score`, `personal_data_exposure_score`, `privacy_violation_count`) are **always included** in every `ExperimentReport`.

## Integration test suite

Q1-oriented integration tests live under `tests/integration/`:

| Test module | Coverage |
| ----------- | -------- |
| `test_pipeline_end_to_end.py` | Full pipeline and CLI |
| `test_privacy_guarantees.py` | Privacy metrics on all protocols |
| `test_graph_reasoning.py` | Graph orchestration protocol |
| `test_simulation_evaluation.py` | Reproducibility, reports, paper integrity |

Run:

```bash
pytest tests/integration/ -m integration -v
```

## Legacy baselines

| CLI name | Class | Maps to protocol |
| -------- | ----- | ---------------- |
| `single_modality` | `SingleModalityBaseline` | `single_modality_baseline` |
| `rule_based` | `RuleBasedFusionBaseline` | `rule_based_fusion_baseline` |
| `dualexis_semantic` | `DualexisSemanticBaseline` | partial (no full pipeline) |

## Evaluation objectives

| Objective | Research questions | Metric categories |
| --------- | ------------------- | ----------------- |
| Technical validity | RQ2, RQ6 | Technical |
| Privacy assurance | RQ1, RQ5 | Privacy |
| Orchestration utility | RQ4, RQ7 | Orchestration |
| Robustness | RQ2, RQ6 | Robustness |

## Experimental setup

### Scenarios

Six reproducible simulation scenarios (`dualexis/simulation/scenario.py`):

- `normal_flow`
- `crowd_acceleration`
- `exit_blockage`
- `audio_stress_signal`
- `multimodal_conflict`
- `evacuation_recommendation`

Minimum seeds per scenario: `{0, 7, 42, 99, 123}`.

## Execution phases

### Phase 1: Privacy compliance audit

**Status:** planned; privacy metrics scaffold implemented.

### Phase 2: Controlled functional benchmarks

Run protocols via `dualexis experiment` or `run_experiment()`.

**Status:** scaffold implemented; full benchmark campaigns planned.

### Phase 3: Orchestration and field pilot

**Status:** planned.

## Statistical analysis (planned)

- Bootstrap CIs for latency and F1
- Paired tests for FPR/FNR on matched runs
- Holm–Bonferroni correction for multiple comparisons
- No significance claims without completed experiments

## Reproducibility artifacts

| Artifact | Location |
| -------- | -------- |
| Battery configs | `experiments/configs/*.yaml` |
| Battery runner | `dualexis/experiments/` |
| JSON results | `results/experiments/` |
| Markdown reports | `results/reports/` |
| LaTeX table scaffold | `paper/tables/results.tex` |
| Protocol definitions | `dualexis/evaluation/protocol.py` |
| Experiment runner | `dualexis/evaluation/experiment.py` |
| Metric computations | `dualexis/evaluation/metrics.py` |
| Integration tests | `tests/integration/test_simulation_evaluation.py` |
| Simulation | `dualexis/simulation/` |

## Related documentation

- [Simulation environment](simulation.md)
- [Framework overview](framework.md)
- [Pipeline](pipeline.md)
