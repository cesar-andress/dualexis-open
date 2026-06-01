# Reproduce validation results

## One-shot

```bash
bash artifact/commands.sh
```

## Step-by-step

```bash
pip install -e ".[dev]"
python3.12 -m dualexis.cli experiment validate-tsgg
python3.12 -m dualexis.cli experiment leakage-audit --fast
python3.12 -m dualexis.cli experiment formal-governance-audit
python3.12 -m pytest tests/unit -q
```

Outputs land under `results/` (runtime) and refresh `results_reference/tables/*.tex` where applicable.
