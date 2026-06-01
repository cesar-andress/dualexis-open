# Expected outputs

| Path | Command |
|------|---------|
| `results/baseline_comparison/results.csv` | `validate-tsgg` |
| `results/privacy_fuzz/privacy_fuzz_results.csv` | `validate-tsgg` |
| `results_reference/tables/harness_honesty.tex` | `validate-tsgg` |
| `results_reference/tables/privacy_fuzz_results.tex` | `validate-tsgg` |
| `results_reference/tables/leakage_audit.tex` | `leakage-audit --fast` |
| `results/leakage_audit/` | `leakage-audit --fast` |
| `results/governance/formal/` | `formal-governance-audit` |

```bash
grep -q 'tab:harness-honesty' results_reference/tables/harness_honesty.tex
python3.12 -m pytest tests/unit -q
```
