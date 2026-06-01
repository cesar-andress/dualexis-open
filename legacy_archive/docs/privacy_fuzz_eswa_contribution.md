# Privacy fuzz battery — ESWA contribution assessment

## Verdict

| Venue framing | Publishable? | Notes |
|---------------|--------------|-------|
| **Standalone full paper** | **Weak** | 10 probes, 100% pass, single policy, no coverage metric, no adaptive attacker |
| **Methodological subsection in DUALEXIS (ESWA)** | **Strong** | Fits trustworthy DSS + operational AI; reproducible CLI + tables |
| **Short ESWA method / software note** | **Medium** | Requires extensions below |

## What elevates it beyond "a test suite"

1. **Explicit threat model** (assets, adversary, TB1–TB5) — `tab:privacy-fuzz-threat-model`
2. **Attack taxonomy** (I1, B1, M1, N1, O1, A0) — `tab:privacy-fuzz-taxonomy`
3. **Fail-closed oracle** with pre-registered expectations
4. **Runtime vs training-time distinction** (Table in `privacy_fuzz_methodology.tex`)
5. **Dual enforcement surfaces**: flat payload validator + `PerceptionFrame` TB1 probe
6. **Reproducible export** (CSV + LaTeX + pytest parametrisation over `FORBIDDEN_FIELDS`)

## Gaps before standalone paper

- Coverage score: |probes| / |FORBIDDEN_FIELDS ∪ obfuscation grammar|
- Negative tests for fail-open regressions
- TB2–TB5 boundary-specific probe matrix
- Mutation-based key generation (not only hand-authored cases)
- Comparison to redact-and-continue baselines

## Commands

```bash
python3.12 -m dualexis.cli experiment empirical-eswa   # includes fuzz export
# or export only:
python3.12 -c "from dualexis.evaluation.privacy_fuzz_battery import export_privacy_fuzz_results; export_privacy_fuzz_results('results/privacy_fuzz')"
pytest tests/unit/test_privacy_fuzz_battery.py tests/unit/test_validation_privacy_fuzz.py -q
```
