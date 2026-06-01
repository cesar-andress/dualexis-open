# DUALEXIS Repository Alignment Policy

This document defines how functional modules in the DUALEXIS codebase stay aligned
across four artifacts:

1. **Python implementation** — package under `dualexis/<module>/`
2. **Automated tests** — at least one file under `tests/`
3. **Documentation** — module `README.md` and/or a dedicated `docs/*.md` section
4. **LaTeX paper** — a related section under `results_reference/sections/` when the module
   contributes to the research framework

The goal is to prevent undocumented architectural drift: every core layer must remain
traceable from code to tests, docs, and (where applicable) the design article.

## Scope

### In scope (core functional modules)

These nine packages implement the six-layer framework (L1–L6) plus pipeline,
simulation, and evaluation scaffolding:

| Module | Layer / role | Python package | Documentation | Tests (name fragment) | Paper section |
| ------ | ------------ | -------------- | ------------- | --------------------- | ------------- |
| Privacy Runtime | L1 | `dualexis/privacy_runtime/` | `docs/privacy.md`, `README.md` | `privacy_runtime` | `privacy_threats_governance.tex` |
| Edge Perception | L2 | `dualexis/edge_perception/` | `README.md`, `docs/framework.md` | `edge_perception` | `framework.tex` |
| Semantic Events | L3 | `dualexis/semantic_events/` | `docs/event_taxonomy.md`, `README.md` | `semantic_events`, `event_taxonomy` | `event_model.tex` |
| Temporal Graph | L4 | `dualexis/temporal_graph/` | `docs/temporal_graph.md`, `README.md` | `temporal_graph` | `temporal_graph.tex` |
| Local Reasoning | L5 | `dualexis/local_reasoning/` | `docs/local_reasoning.md`, `README.md` | `local_reasoning` | `local_reasoning.tex` |
| Orchestration | L6 | `dualexis/orchestration/` | `README.md`, `docs/framework.md` | `orchestration` | `framework.tex` |
| Pipeline | End-to-end | `dualexis/pipeline/` | `docs/pipeline.md` | `pipeline` | `pipeline.tex` |
| Simulation | Synthetic data | `dualexis/simulation/` | `docs/simulation.md`, `README.md` | `simulation` | `methodology.tex` |
| Evaluation | Metrics scaffold | `dualexis/evaluation/` | `docs/evaluation.md`, `README.md` | `evaluation` | `metrics.tex` |

For documentation, **at least one** path in the Documentation column must exist.
For tests, **at least one** file under `tests/` whose stem contains a listed fragment
must exist.

### Out of scope (supporting packages)

The following packages are intentionally excluded from the core registry:

- `dualexis/core/`, `dualexis/schemas/` — shared infrastructure (covered by
  `test_core_domain_models.py`, `test_schemas.py`, `test_domain_schemas.py`)
- `dualexis/cli.py`, `dualexis/paper/` — tooling (covered by `test_cli.py`,
  `test_paper_check.py`, and README CLI checks)
- Legacy or placeholder packages (`perception/`, `privacy/`, `fusion/`, `graph/`,
  `reasoning/`, `federation/`, `audit/`) — not part of the six-layer reference path

When a legacy package is promoted to a core layer, add a row to the registry and
extend `tests/test_documentation_alignment.py`.

## Paper sections

All sections listed in `dualexis/paper/check.py` (`REQUIRED_PAPER_SECTIONS`) must
exist on disk. The alignment test imports that list so paper checks stay single-sourced.

Additional cross-cutting sections (e.g. `edge_infrastructure.tex`, `reproducibility.tex`)
are included in the same required set.

## CLI alignment

The root `README.md` is the user-facing CLI contract. Every `` `dualexis <command>` ``
reference in the CLI Usage table and command examples must map to a registered Typer
command in `dualexis/cli.py`.

Currently documented commands: `version`, `check`, `test`, `simulate`, `run-pipeline`,
`evaluate`, `paper-check`, `lint`, `format`.

## Adding or changing a module

1. Implement the package under `dualexis/<module>/`.
2. Add or update `dualexis/<module>/README.md` **or** a `docs/<topic>.md` section.
3. Add at least one test file whose name reflects the module.
4. If the module contributes to the research narrative, add or extend a LaTeX section
   and register it in `dualexis/paper/check.py`.
5. Update the registry in `tests/test_documentation_alignment.py` and this table.
6. Run `uv run pytest tests/test_documentation_alignment.py`.

## Enforcement

Alignment is enforced by:

```bash
uv run pytest tests/test_documentation_alignment.py
```

This test is included in the default CI test suite. Failures block merge until the
missing artifact (doc, test, or paper section) is restored.

See also `results_reference/sections/reproducibility.tex` for the research-facing statement of
this policy.
