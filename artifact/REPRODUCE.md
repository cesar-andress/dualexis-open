# Reproduce JSS validation results

These commands regenerate the tables and audit artefacts referenced in `results_reference/ (CSV and summary tables)` and `results_reference/tables/`.

## One-shot reproduction

```bash
bash artifact/commands.sh
```

## Step-by-step

### 1. Install

```bash
pip install -e .
```

### 2. Full TSGG validation package

Regenerates harness honesty and privacy fuzz LaTeX tables:

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

### 5. Unit tests

```bash
python3.12 -m pytest tests/unit -q
```

## Build manuscript PDF

```bash
python3.12 artifact/commands.sh --latex-only
```

Output: `paper/main_jss.pdf` and `dist/jss_submission_package/`.

## Expected outputs

See `expected_outputs.md` for file paths and sanity checks.

## Runtime notes

- Full multiseed validation (`validate-tsgg`) takes several minutes on a laptop.
- `--fast` flags on audit commands reduce Monte Carlo samples for quicker smoke tests.
- All experiments use bundled synthetic scenarios; no external datasets are required.
