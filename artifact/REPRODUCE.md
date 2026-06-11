# Reproduce JSS validation results

**Release:** v1.0.3 · **GitHub:** https://github.com/cesar-andress/dualexis-open · **Zenodo:** https://doi.org/10.5281/zenodo.20499184

These commands regenerate the tables and audit artefacts referenced in `results_reference/ (CSV and summary tables)` and `results_reference/tables/`.

## One-shot reproduction

```bash
bash artifact/commands.sh
```

The script clears regeneratable outputs first (`artifact/clean.sh results-only`), then installs,
runs the validation harness, and executes unit tests.

## Full clean (artifact evaluation prep)

```bash
bash artifact/clean.sh full
```

Removes caches, LaTeX intermediates, legacy experiment outputs, and duplicate results.
See `ARTIFACT_EVALUATION.md` for the complete checklist.

## Step-by-step

### 1. Install

```bash
pip install -e .
```

### 2. Full TSGG validation package

Regenerates privacy fuzz and baseline LaTeX tables:

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

### 7. Unit tests

```bash
python3.12 -m pytest tests/unit -q
```

## Manuscript (out of scope)

```bash
python3.12 artifact/commands.sh
```

The JSS manuscript is not included in this repository. and .

## Expected outputs

See `expected_outputs.md` for file paths and sanity checks.

## Runtime notes

- Full multiseed validation (`validate-tsgg`) takes several minutes on a laptop.
- `--fast` flags on audit commands reduce Monte Carlo samples for quicker smoke tests.
- All experiments use bundled synthetic scenarios; no external datasets are required.
