# TSGG (Trusted Safety State Governance Graph)

TSGG is an open-source trace architecture for auditable human-AI systems.

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

This repository is the reference implementation and validation harness companion to the Journal of Systems and Software TSGG manuscript. It does not contain the manuscript source.

## Contents

| Component | Location | Purpose |
|-----------|----------|---------|
| Reference implementation | `dualexis/` | Trace export, privacy ingress, governance FSM, audit hooks |
| Validation harness | `dualexis.cli experiment …` | Regenerate validation tables and audit artefacts |
| Pinned outputs | `results_reference/` | Reference CSV/JSON/LaTeX fragments for diff review |
| Reproduction docs | `artifact/` | Install, commands, expected outputs, AE guide |

See `ARTIFACT_EVALUATION.md` for the JSS artifact evaluation checklist.

## Quick start

```bash
pip install -e ".[dev]"
bash artifact/commands.sh
```

Or run steps individually; see `INSTALL.md` and `REPRODUCE.md`.

## Scope

This artefact supports simulation-based software validation: trace export execution, invariant checks, benchmark leakage disclosure, and reproducible diagnostics. It does not claim field deployment outcomes or user studies.

## Citation

See `CITATION.cff`. Please cite both the JSS paper (when available) and this software release.

## License

Apache-2.0. See `LICENSE`.
