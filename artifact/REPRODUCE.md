# Reproduce validation results results

Release: v1.0.4 | GitHub: https://github.com/cesar-andress/dualexis-open | Zenodo: https://doi.org/10.5281/zenodo.20499184

These commands regenerate the tables and audit artefacts referenced in `results_reference/tables/` and `results/` (CSV/JSON).

## One-shot reproduction

```bash
bash artifact/commands.sh
```

The script clears regeneratable outputs first (`artifact/clean.sh results-only`), then installs,
runs the validation harness, exports Tables 7-8, and executes the reproduction test suite.

## Full clean (reproducibility prep)

```bash
bash artifact/clean.sh full
```

Removes caches, LaTeX intermediates, legacy experiment outputs, and duplicate results.
See `ARTIFACT_EVALUATION.md` for the complete checklist.

## Step-by-step

### 1. Install

```bash
pip install -e ".[dev]"
```

### 2. Full TSGG validation package

Regenerates privacy fuzz, baseline LaTeX tables, and B5 baseline CSV:

```bash
python3.12 -m dualexis.cli experiment validate-tsgg
```

### 3. Leakage audit

```bash
python3.12 -m dualexis.cli experiment leakage-audit --fast
```

Writes `results_reference/tables/leakage_audit.tex` and CSV under `results/leakage_audit/`.

### 4. Formal governance audit

```bash
python3.12 -m dualexis.cli experiment formal-governance-audit
```

Writes governance metrics under `results/governance/formal/`.

### 5. Trust propagation (mean path trust for Table 7)

```bash
python3.12 -m dualexis.cli experiment tsgg-trust-propagation --fast --seeds 1,2,3
```

Writes `results/tsgg/trust/trust_propagation_report.json`.

### 6. Harness honesty export (Table 7)

```bash
python3.12 -m dualexis.cli experiment export-harness-honesty
```

Reads leakage, privacy fuzz, governance, and trust artefacts; writes
`results_reference/tables/harness_honesty.tex`.

### 7. Harness B5 labels export (Table 8)

```bash
python3.12 -m dualexis.cli experiment export-harness-b5-labels
```

Reads `results/baseline_comparison/results.csv` (B5 rows); classifies Pass/Partial/Fail from
mean `event_detection_accuracy` (Pass $=1.0$, Fail $=0.0$, Partial otherwise); writes
`results_reference/tables/harness_b5_by_scenario.tex`.

### 8. reproduction test suite

```bash
python3.12 -m pytest tests/artifact tests/unit \
  --ignore=tests/unit/test_paper_check.py \
  --ignore=tests/unit/test_pipeline.py \
  --ignore=tests/unit/test_edge_runtime.py \
  -q
```

## Independent ground truth (E2, optional)

Regenerate frozen YAML labels from rules (not required for main-text `commands.sh`):

```bash
python3.12 scripts/generate_independent_ground_truth.py
```

See `docs/e2_independent_ground_truth.md`.

## Manuscript (out of scope)

The manuscript is maintained in a separate private repository and is not included in this artefact.

## Expected outputs

See `expected_outputs.md` for file paths and sanity checks.

## Runtime notes

- Full multiseed validation (`validate-tsgg`) takes several minutes on a laptop.
- `--fast` flags on audit commands reduce Monte Carlo samples for quicker smoke tests.
- All experiments use bundled synthetic scenarios; no external datasets are required.
