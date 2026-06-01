# TSGG (Trusted Safety State Governance Graph)

TSGG is an open-source trace architecture for auditable human–AI systems.

The framework represents:

```
Evidence
  → Safety State
  → Causal Transition
  → Recommendation
  → Governance Decision
  → Audit Trace
```

and supports:

- privacy admissibility constraints
- governance-aware decision traces
- benchmark leakage auditing
- reproducible validation harnesses

This repository contains the reference implementation used in the accompanying *Journal of Systems and Software* manuscript.

## Contents

| Component | Location | Purpose |
|-----------|----------|---------|
| Reference implementation | `dualexis/` | Trace export, privacy ingress, governance FSM, audit hooks |
| Validation harness | `dualexis.cli experiment …` | Regenerate paper tables and audit artefacts |
| Manuscript source | `paper/main_jss.tex` | JSS manuscript |
| Reproduction docs | `artifact/` | Install, commands, expected outputs |

## Quick start

```bash
pip install -e .
bash artifact/commands.sh
```

Or run steps individually — see `INSTALL.md` and `REPRODUCE.md`.

## Scope

This artefact supports **simulation-based software validation**: trace completeness, invariant checks, benchmark leakage disclosure, and reproducible diagnostics. It does **not** claim field deployment outcomes or user studies.

## Citation

See `CITATION.cff`. Please cite both the JSS paper (when available) and this software release.

## License

Apache-2.0 — see `LICENSE`.
