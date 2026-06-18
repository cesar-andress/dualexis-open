# Audit comparison methodology (Phase 2)

This document describes the post-hoc trace auditability comparison between TSGG native exports and baseline trace formats. It supports synthetic validation evidence only; it does **not** claim operational safety, detector superiority, or improved human decision outcomes.

## Scientific framing

The comparison evaluates whether an auditor can answer structured questions from exported traces after a run completes. All formats are derived from the **same underlying** `TsggRunRecord` produced by `run_tsgg_record()`. Metrics report query success, completeness, information loss, and violation-detection F1 under injected mutations—not live deployment performance.

Reference leakage score \(L_S\) (currently ~0.575 after Phase 1 procedural alignment) is reported transparently in task A6 and summary artefacts.

## Export formats

| Format | Module | Information retained |
| --- | --- | --- |
| TSGG native | `tsgg_native_exporter.py` | Typed nodes, links, governance, causal, leakage metadata |
| Flat JSON | `flat_json_exporter.py` | Chronological event records without typed graph schema |
| PROV-style | `prov_exporter.py` | Entity/activity/agent derivations (simplified PROV-JSON) |
| XES-style | `xes_exporter.py` | Case/activity/timestamp/lifecycle/attributes (simplified XES JSON) |

Build entry point: `build_audit_trace_exports(record, leakage_report=...)`.

## Audit tasks (A1–A7)

| ID | Kind | Question |
| --- | --- | --- |
| A1 | Query | Reconstruct evidence-to-recommendation chain |
| A2 | Violation | Detect review-required recommendation without governance disposition |
| A3 | Violation | Detect forbidden privacy key in trace projection |
| A4 | Query | Identify supporting evidence for a causal state transition |
| A5 | Violation | Verify append-only governance step ordering |
| A6 | Query | Locate benchmark-coupling disclosure fields |
| A7 | Query | Count affected zones in multi-zone evacuation pattern |

Each task has deterministic gold answers in `gold_generator.py` and format-specific evaluators in `queries.py`.

## Mutations

Injected on exported payloads before violation-detection evaluation:

- `remove_governance_disposition` — strips institutional disposition records (A2)
- `inject_forbidden_privacy_key` — adds a forbidden attribute (A3)
- `reorder_governance_steps` — permutes governance ordering (A5)
- `remove_supporting_evidence_link` — drops causal evidence link (A4 mutation path)
- `remove_leakage_metadata` — removes benchmark coupling fields (A6 mutation path)

Mutations are applied uniformly across all export formats so comparisons are fair: baselines fail only when the information is absent from that format's natural representation.

## Metrics

| Metric | Definition |
| --- | --- |
| Query success rate (QSR) | Fraction of applicable clean-query tasks answered correctly |
| Completeness | Overlap between returned and gold answer sets (Jaccard-style) |
| Information loss | \(1 - \text{completeness}\) aggregated over clean queries |
| Violation F1 | F1 for mutation tasks where gold expects positive detection |
| Mean query hops | Average traversal steps for successful queries (when defined) |

## Experiment battery

Command:

```bash
python3.12 -m dualexis.cli experiment audit-comparison
```

Default design: 6 paper scenarios × 30 seeds. Outputs under `results_reference/audit_comparison/`:

- `audit_comparison_results.csv` — per-format aggregate metrics
- `audit_task_results.csv` — per-run/per-task/per-format rows
- `audit_comparison_summary.json` — run metadata and aggregates
- `audit_comparison.tex` — LaTeX table fragment
- `exports/{format}/{scenario}_seed{N}.json` — pinned baseline exports

Single-run baseline export:

```bash
python3.12 -m dualexis.cli experiment export-audit-baselines --scenario exit_blockage --seed 1
```

## Fairness and tautology mitigation

1. **Same run record** — all exporters consume one `TsggRunRecord`; no format-specific re-simulation.
2. **Natural representation limits** — flat JSON cannot express typed links; PROV/XES map only fields that fit their schema. Tasks fail on baselines only when required fields are genuinely unavailable.
3. **Machine-checkable gold** — gold is generated from the run record, not from TSGG-specific query code.
4. **A7 scenario scope** — zone counting applies only to `evacuation_recommendation`; other scenarios mark the task not applicable.
5. **No operational claims** — disclaimer embedded in summary JSON and LaTeX caption.

## Phase 3 scaffold

Future work (not in this phase): manuscript integration, reviewer-facing task narratives, and extended mutation suites. Module layout under `dualexis/evaluation/audit_tasks/` is stable for extension via `task_registry.py`.
