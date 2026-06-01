# Release notes — v1.0.0

**Title:** TSGG Reference Implementation  
**Repository:** https://github.com/cesar-andress/dualexis-open  
**Tag:** `v1.0.0`  
**Date:** 2026-06-01  
**License:** Apache-2.0

## Purpose

First public archival release of the **Trusted Safety State Governance Graph (TSGG)** reference implementation and validation harness for *Journal of Systems and Software* (JSS) software-artefact evaluation and **Zenodo DOI** minting.

## What this release contains

- Python package `dualexis` — trace export, privacy ingress (A1), governance FSM (A4), append-only audit (A5)
- Validation harness CLI — `validate-tsgg`, `leakage-audit`, `formal-governance-audit`
- Reproduction scripts — `artifact/commands.sh`, `artifact/REPRODUCE.md`, `artifact/expected_outputs.md`
- Pinned reference outputs under `results_reference/`

## TSGG trace chain

```
Evidence → Safety State → Causal Transition → Recommendation → Governance Decision → Audit Trace
```

Supported capabilities:

- privacy admissibility constraints (fail-closed ingress, fuzz regression)
- governance-aware decision traces (FSM macro-states, audit append-only semantics)
- benchmark leakage auditing (procedural / distributional independence metrics)
- reproducible validation harnesses (scripted table regeneration, unit tests)

## Reproduce validation results

```bash
pip install -e ".[dev]"
bash artifact/commands.sh
```

Expected outputs are documented in `artifact/expected_outputs.md`.

## Citation

**Software (this release):**

```bibtex
@software{tsgg_reference_implementation_v1_0_0,
  author       = {Moncunill, David Mart{\'i}n and S{\'a}nchez, C{\'e}sar Andr{\'e}s},
  title        = {{TSGG} Reference Implementation},
  year         = {2026},
  version      = {v1.0.0},
  url          = {https://github.com/cesar-andress/dualexis-open}
}
```

Zenodo DOI will be added after archival.

**Paper (when published):**

*Trusted Safety State Governance Graphs: A Software Trace Architecture for Auditable Human–AI Safety Systems* — *Journal of Systems and Software*.

See `CITATION.cff` for machine-readable metadata.

## Zenodo archival checklist

1. Connect GitHub repository to Zenodo (or upload release archive manually).
2. Create GitHub release **`v1.0.0`** from this tag; Zenodo ingests `.zenodo.json` metadata.
3. Publish Zenodo record; copy minted DOI into `CITATION.cff` and `artifact/CITATION.cff`.
4. Add Zenodo badge to `README.md` after DOI assignment (optional).

## Known scope limits

- Simulation-based software validation only; no field-deployment or user-study claims
- Synthetic scenarios bundled; no external datasets required
- JSS paper DOI to be linked after acceptance/publication

## Authors

- David Martín Moncunill — Conceptualization, Methodology, Software, Formal analysis, Investigation, Writing
- César Andrés Sánchez — Conceptualization, Methodology, Validation, Investigation, Supervision, Writing
