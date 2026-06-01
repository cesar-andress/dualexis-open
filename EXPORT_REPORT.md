# Export report — dualexis-open

Generated: 2026-06-01T20:25:24.718823+00:00
Source monorepo: `/home/cesar/dualexis`

## Removed

- `legacy_archive/`
- `apps/`
- `uv.lock`
- `cleanup_report.md`
- `tests/legacy_archive/`
- `tests/unit/test_edge_runtime.py`

## Remaining TeX files

- `dualexis/cssg/assets/causal_state_graph.tex` — Standalone TikZ diagram source for causal graph export
- `dualexis/tsgg/assets/tsgg_framework.tex` — Standalone TikZ diagram source for TSGG pipeline figure generation
- `results_reference/baseline_comparison/analysis/multiseed_figures.tex` — Validation harness LaTeX table export (CSV is canonical; TeX is optional diff artefact)
- `results_reference/baseline_comparison/analysis/multiseed_statistics.tex` — Validation harness LaTeX table export (CSV is canonical; TeX is optional diff artefact)
- `results_reference/tables/baseline_results.tex` — Validation harness LaTeX table export (CSV is canonical; TeX is optional diff artefact)
- `results_reference/tables/harness_honesty.tex` — Validation harness LaTeX table export (CSV is canonical; TeX is optional diff artefact)
- `results_reference/tables/leakage_audit.tex` — Validation harness LaTeX table export (CSV is canonical; TeX is optional diff artefact)
- `results_reference/tables/privacy_fuzz_results.tex` — Validation harness LaTeX table export (CSV is canonical; TeX is optional diff artefact)

## Grep scan (forbidden patterns)

- `OPEN_SOURCE_READINESS_REPORT.md:35`: - **PASS** — no ESWA paths outside legacy_archive: []
- `OPEN_SOURCE_READINESS_REPORT.md:36`: - **PASS** — no paper/ directory
- `CONTRIBUTING.md:22`: Paper/LaTeX changes belong in the separate manuscript repository.
- `.gitignore:79`: # paper/ excluded from open repo
- `.gitignore:82`: # paper/ excluded from open repo
- `.gitignore:85`: # paper/ excluded from open repo
- `.gitignore:88`: # paper/ excluded from open repo
- `.gitignore:91`: # paper/ excluded from open repo
- `.gitignore:94`: # paper/ excluded from open repo
- `.gitignore:97`: # paper/ excluded from open repo
- `.gitignore:100`: # paper/ excluded from open repo
- `.gitignore:103`: # paper/ excluded from open repo
- `.gitignore:106`: # paper/ excluded from open repo
- `.gitignore:109`: # paper/ excluded from open repo
- `.gitignore:112`: # paper/ excluded from open repo
- `.gitignore:115`: # paper/ excluded from open repo
- `.gitignore:118`: # paper/ excluded from open repo
- `.gitignore:121`: # paper/ excluded from open repo
- `.gitignore:124`: # paper/ excluded from open repo
- `CHANGELOG.md:18`: - Manuscript build chain — `paper/main_jss.tex`, `scripts/build_jss_submission.py`
- `CHANGELOG.md:79`: - `paper/data_availability_statement.txt`
- `artifact/REPRODUCE.md:55`: Output: `paper/main_jss.pdf` and `dist/jss_submission_package/`.
- `artifact/README.md:31`: | Manuscript source | `paper/main_jss.tex` | JSS manuscript |
- `artifact/EXPECTED_OUTPUTS.md:33`: | `paper/main_jss.pdf` | `python3.12 artifact/commands.sh --latex-only` |
- `dualexis/cli.py:440`: "paper/tables/results.tex",
- `dualexis/cli.py:888`: typer.echo(report.reviewer_statement)
- `dualexis/cli.py:1365`: typer.echo(f"Narrative: {out_path / 'narrative_eswa.md'}")
- `dualexis/cli.py:1392`: "paper/tables/results.tex",
- `docs/privacy.md:142`: - LaTeX: `paper/sections/privacy_threats_governance.tex`
- `docs/evaluation.md:5`: Formal LaTeX definitions: `paper/sections/metrics.tex` and `paper/sections/evaluation_plan.tex`.
- `docs/evaluation.md:6`: Threat model: `docs/threat_model.md` and `paper/sections/privacy_threats_governance.tex`.
- `docs/evaluation.md:38`: dualexis experiment paper-table --input results/experiments/ --output paper/tables/results.tex
- `docs/evaluation.md:72`: See `paper/sections/results_scaffold.tex` for interpretation guardrails.
- `docs/evaluation.md:229`: | LaTeX table scaffold | `paper/tables/results.tex` |
- `docs/edge_infrastructure.md:289`: | Paper section | `paper/sections/edge_infrastructure.tex` |
- `docs/e2_independent_ground_truth.md:31`: MET --> TEX["paper/tables/e2_independent_gt.tex"]
- `docs/e2_independent_ground_truth.md:32`: TEX --> RT["paper/sections/results.tex auto-sync"]
- `docs/e2_independent_ground_truth.md:57`: | `paper/tables/e2_independent_gt.tex` | LaTeX table (`tab:e2-independent-gt`) |
- `docs/e2_independent_ground_truth.md:79`: --paper-tex paper/tables/e2_independent_gt.tex \
- `docs/e2_independent_ground_truth.md:80`: --results-tex paper/sections/results.tex \
- `docs/e2_independent_ground_truth.md:90`: - **LaTeX:** `paper/tables/e2_independent_gt.tex` — Table~\ref{tab:e2-independent-gt} (mean Acc./FPR/FNR/$S_{\mathrm{exp
- `docs/e2_independent_ground_truth.md:91`: - **Manuscript hook:** `paper/sections/results.tex` block between `% <e2-auto-tables>` … `% </e2-auto-tables>` (auto-upd
- `docs/temporal_graph.md:103`: - LaTeX: `paper/sections/temporal_graph.tex`
- `docs/event_taxonomy.md:221`: - LaTeX: `paper/sections/event_taxonomy.tex`
- `docs/safety_graph.md:372`: - [Event Model (paper)](../paper/sections/event_model.tex)
- `docs/threat_model.md:9`: - `docs/privacy.md` and `paper/sections/privacy_threats_governance.tex` (privacy, threats, governance; TB1–TB5)
- `docs/threat_model.md:10`: - `paper/sections/threats_to_validity.tex` (evaluation validity, not operational security)
- `docs/threat_model.md:64`: Trust boundaries TB1–TB5 structure transitions from ephemeral input to auditable semantic publication (`paper/sections/p
- `docs/threat_model.md:185`: protocol in `paper/sections/evaluation_plan.tex`. Empirical validation of
- `docs/threat_model.md:187`: (`paper/sections/future_work.tex`).
