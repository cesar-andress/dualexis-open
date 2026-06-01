# Export report — dualexis-open

Generated: 2026-06-01T20:28:12.809319+00:00
Source monorepo: `/home/cesar/dualexis`

## Removed

- `legacy_archive/`
- `apps/`
- `uv.lock`
- `cleanup_report.md`
- `OPEN_SOURCE_READINESS_REPORT.md`
- `tests/legacy_archive/`
- `tests/unit/test_edge_runtime.py`

## Remaining TeX files

- `dualexis/cssg/assets/causal_state_graph.tex` — Standalone TikZ source for causal graph export
- `dualexis/tsgg/assets/trust_flow_graph.tex` — review
- `dualexis/tsgg/assets/tsgg_framework.tex` — Standalone TikZ source for TSGG pipeline figure export
- `paper/tables/multiseed_statistics.tex` — review
- `results_reference/baseline_comparison/analysis/multiseed_figures.tex` — Validation harness LaTeX table export (CSV is canonical)
- `results_reference/baseline_comparison/analysis/multiseed_statistics.tex` — Validation harness LaTeX table export (CSV is canonical)
- `results_reference/sections/formal_governance_model.tex` — Validation harness LaTeX table export (CSV is canonical)
- `results_reference/sections/leakage_analysis.tex` — Validation harness LaTeX table export (CSV is canonical)
- `results_reference/tables/baseline_results.tex` — Validation harness LaTeX table export (CSV is canonical)
- `results_reference/tables/harness_honesty.tex` — Validation harness LaTeX table export (CSV is canonical)
- `results_reference/tables/leakage_audit.tex` — Validation harness LaTeX table export (CSV is canonical)
- `results_reference/tables/privacy_fuzz_results.tex` — Validation harness LaTeX table export (CSV is canonical)

## Grep scan

- `docs/development.md:25`: paper/              # LaTeX research paper
- `docs/alignment_policy.md:44`: - `dualexis/cli.py`, `dualexis/paper/` — tooling (covered by `test_cli.py`,
- `docs/alignment_policy.md:54`: All sections listed in `dualexis/paper/check.py` (`REQUIRED_PAPER_SECTIONS`) must
- `docs/alignment_policy.md:75`: and register it in `dualexis/paper/check.py`.
- `tests/test_documentation_alignment.py:146`: f"{module.name}: missing paper section paper/{module.paper_section}"
- `scripts/sync_public_jss_artifact.py:57`: ("paper/tables/baseline_results.tex", "results_reference/tables/baseline_results.tex"),
- `scripts/sync_public_jss_artifact.py:58`: ("paper/tables/privacy_fuzz_results.tex", "results_reference/tables/privacy_fuzz_results.tex"),
- `scripts/sync_public_jss_artifact.py:59`: ("paper/tables/e2_independent_gt.tex", "results_reference/tables/e2_independent_gt.tex"),
- `scripts/sync_public_jss_artifact.py:60`: ("paper/tables/results.tex", "results_reference/tables/results.tex"),
- `scripts/sync_public_jss_artifact.py:61`: ('"paper/tables"', '"results_reference/tables"'),
- `scripts/sync_public_jss_artifact.py:62`: ('"paper/sections"', '"results_reference/sections"'),
- `scripts/sync_public_jss_artifact.py:63`: ('"paper/figures"', '"dualexis/tsgg/assets"'),
- `scripts/sync_public_jss_artifact.py:64`: ('typer.Option("paper/tables"', 'typer.Option("results_reference/tables"'),
- `scripts/sync_public_jss_artifact.py:65`: ('typer.Option("paper/sections"', 'typer.Option("results_reference/sections"'),
- `scripts/sync_public_jss_artifact.py:66`: ('typer.Option("paper/figures"', 'typer.Option("dualexis/tsgg/assets"'),
- `scripts/sync_public_jss_artifact.py:67`: ('Path("paper/tables")', 'Path("results_reference/tables")'),
- `scripts/sync_public_jss_artifact.py:68`: ('Path("paper/sections")', 'Path("results_reference/sections")'),
- `scripts/sync_public_jss_artifact.py:69`: ('Path("paper/figures")', 'Path("dualexis/tsgg/assets")'),
- `scripts/sync_public_jss_artifact.py:70`: ("paper/sections/results.tex", "results_reference/sections/results.tex"),
- `scripts/sync_public_jss_artifact.py:71`: ("../paper/sections/", "results_reference/sections/"),
- `scripts/sync_public_jss_artifact.py:72`: ("`paper/sections/", "`results_reference/sections/"),
- `scripts/sync_public_jss_artifact.py:73`: ("`paper/tables/", "`results_reference/tables/"),
- `scripts/sync_public_jss_artifact.py:74`: ("paper/sections/", "results_reference/sections/"),
- `scripts/sync_public_jss_artifact.py:75`: ("paper/tables/", "results_reference/tables/"),
- `scripts/sync_public_jss_artifact.py:76`: ("narrative_eswa.md", "narrative_validation.md"),
- `scripts/sync_public_jss_artifact.py:77`: ("generate_eswa_narrative", "generate_validation_narrative"),
- `scripts/sync_public_jss_artifact.py:78`: ("run_empirical_eswa_package", "run_validate_tsgg_package"),
- `scripts/sync_public_jss_artifact.py:79`: ("reviewer_statement", "independence_disclosure"),
- `scripts/sync_public_jss_artifact.py:80`: ("REVIEWER_STATEMENT", "INDEPENDENCE_DISCLOSURE"),
- `scripts/sync_public_jss_artifact.py:82`: ("ESWA empirical defensibility", "validation harness defensibility"),
- `scripts/sync_public_jss_artifact.py:83`: ("ESWA-style markdown narrative", "Validation markdown narrative"),
- `scripts/sync_public_jss_artifact.py:84`: ("Multiseed statistical analysis narrative (ESWA)", "Multiseed statistical analysis narrative"),
- `scripts/sync_public_jss_artifact.py:85`: ("Interpretation for reviewers:", "Interpretation for validation readers:"),
- `scripts/sync_public_jss_artifact.py:89`: r"ESWA|Expert Systems with Applications|reviewer|camera-ready|\bdraft\b|\bTODO\b|\bFIXME\b|paper/",
- `scripts/sync_public_jss_artifact.py:223`: MONOREPO / "paper/legacy_archive/figures/figures/tsgg_framework.tex",
- `scripts/sync_public_jss_artifact.py:224`: MONOREPO / "paper/figures/tsgg_framework.tex",
- `scripts/sync_public_jss_artifact.py:251`: cssg_src = MONOREPO / "paper/figures/causal_state_graph.tex"
- `scripts/sync_public_jss_artifact.py:306`: start = text.find('@experiment_app.command("empirical-eswa"')
- `scripts/sync_public_jss_artifact.py:581`: def remove_eswa_docs(removed: list[str]) -> None:
- `scripts/sync_public_jss_artifact.py:583`: if path.is_file() and "eswa" in path.name.lower():
- `scripts/sync_public_jss_artifact.py:665`: ("no paper/", not (TARGET / "paper").exists()),
- `scripts/sync_public_jss_artifact.py:738`: remove_eswa_docs(removed)
- `results_reference/sections/leakage_analysis.tex:43`: \paragraph{Reviewer-facing statement.}
- `dualexis/leakage_audit/export.py:109`: \\paragraph{{Reviewer-facing statement.}}
- `docs/diagrams/end_to_end_pipeline.mmd:1`: %% DUALEXIS end-to-end pipeline (L1–L6). Source of truth — copied to paper/figures/.
- `docs/diagrams/README.md:4`: Sources live in this directory; mirrored copies are kept in `paper/figures/`.
- `docs/diagrams/README.md:27`: Individual figure wrappers are in `paper/figures/fig_*.tex`.
- `docs/diagrams/README.md:34`: Or include all figures (draft builds):
- `docs/diagrams/README.md:40`: Compile the paper from `paper/` after rendering PDFs.

## Test result

pytest exit code: 1

## Reproducibility

artifact/commands.sh exit code: 1

## Overall: **FAIL**

