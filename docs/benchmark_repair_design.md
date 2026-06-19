# Benchmark Repair Design: Decoupled Conformance Evaluation for TSGG

**Status:** Design specification (no implementation)  
**Audience:** JSS artifact evaluators, manuscript reviewers, maintainers  
**Repository:** `dualexis` reference implementation (`~/papers/dualexis/dualexis`)  
**Date:** 2026-06-18  

---

## Executive summary

The current B5 conformance benchmark achieves perfect multiseed agreement (accuracy = 1.0, FPR = 0, FNR = 0) because the simulator event emitter and the ground-truth labeler evaluate **the same procedural YAML rule specifications** over the **same world-state trajectory**. The leakage audit correctly reports elevated coupling (\(L_S \approx 0.575\), `shared_variables_ratio = 1.0`). Reviewers interpret this as **benchmark self-agreement**, not independent validation.

This document specifies a **decoupled benchmark architecture** that preserves reproducibility, minimizes repository disruption, and replaces headline Pass/Fail labels with **Procedural Agreement Rate (PAR)** and robustness statistics under threshold perturbation.

**Recommended architecture:** **Alternative A (Independent emission profiles)** as the primary benchmark, with **Alternative B (held-out GT rules)** as a supplementary stress test and **Alternative C (oracle GT)** as an upper-bound diagnostic only.

---

## 1. Current dependency structure and circularity mechanism

### 1.1 Component graph (as implemented)

```
experiments/ground_truth/rules/{scenario}.yaml
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
 rule_driven_emitter.py          independent_labeler.py
 (via SyntheticEventGenerator)   (via build_independent_ground_truth)
         │                              │
         │  load_ground_truth_rules()   │  load_ground_truth_rules()
         │  rule_matches_tick()         │  rule_matches_tick()
         │                              │
         └──────────┬───────────────────┘
                    ▼
            world_dynamics(seed)
            → WorldState per tick
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
   SemanticEvents          GroundTruthLabels
         │                     │
         └──────────┬──────────┘
                    ▼
         B5 alignment (comparable_baselines.py)
         compute_event_detection_accuracy()
```

### 1.2 Why “independent labeler” is procedurally coupled

The labeler is **independent** only in the sense of **Python import isolation**:

- `independent_labeler.py` does not import `event_generator.py` (checked by AST in `leakage_audit/spec_extraction.py`).
- Both modules import **`gt_rules.py`** and read **`experiments/ground_truth/rules/`**.

Semantic independence is therefore **not** specification independence.

### 1.3 Leakage audit reflects shared specification

`spec_extraction.py` extracts emitter thresholds by **re-reading GT YAML** into component `rule_driven_emitter`. Overlap with `ground_truth_rules` yields:

| Overlap component | Current typical value | Interpretation |
|-------------------|----------------------|----------------|
| `shared_variables_ratio` | 1.0 | Same world metrics feed both paths |
| `shared_threshold_ratio` | ~0.5 | Same rule predicates appear in both specs |
| `shared_logic_ratio` | 0.0 | Different predicate packaging |
| \(L_S\) | ~0.575 | Composite coupling (weights 0.35/0.45/0.20) |

Formula (unchanged, for reference):

\[
L_S = 0.35 \cdot r_{\mathrm{vars}} + 0.45 \cdot r_{\mathrm{thr}} + 0.20 \cdot r_{\mathrm{logic}}
\]

where each \(r_{\cdot}\) is a Jaccard-style overlap ratio across `{world_dynamics, event_generator, ground_truth_rules}`.

### 1.4 Regression test encodes tautology

`tests/unit/test_rule_driven_event_emission.py::test_emitter_matches_independent_labeler_keys_for_all_scenarios` requires:

\[
\text{Counter}(\text{event keys}) = \text{Counter}(\text{label keys})
\]

for all scenarios and seed 17. This test **asserts self-agreement as correctness**, which is scientifically inverted for an evaluation benchmark.

### 1.5 Pipeline path does not break circularity

B5 for `DUALEXIS_FULL_PIPELINE` compares pipeline-normalized events (after L3–L6) to procedural GT built with the **same seed walk**. When the simulator emits labels isomorphic to GT rules, and the pipeline preserves simulator semantics, perfect B5 scores follow **by construction**, not by empirical discovery.

---

## 2. Decoupled benchmark architecture (target state)

### 2.1 Separation of concerns

Four subsystems with **explicit, non-shared specification boundaries**:

| Subsystem | Role | Specification source | Runtime reads GT? |
|-----------|------|---------------------|-------------------|
| **World simulator** | Deterministic dynamics | `world_dynamics.py` + scenario params | No |
| **Event generator** | Observations (imperfect) | `experiments/simulator/emission_profiles/` | **No** |
| **Ground-truth oracle** | Reference labels | `experiments/ground_truth/rules/` | N/A (eval only) |
| **Evaluation harness** | Metrics, leakage, audit | `experiments/benchmark_manifest.yaml` | Offline only |

### 2.2 Data flow (decoupled)

```
ScenarioId + seed
       │
       ▼
┌──────────────────┐
│  World simulator │  world_dynamics.advance_world_state()
└────────┬─────────┘
         │ WorldState_t
         ├─────────────────────────────┐
         ▼                             ▼
┌─────────────────────┐    ┌──────────────────────┐
│ Event generator     │    │ Ground-truth oracle   │
│ (emission profiles) │    │ (GT rules YAML)       │
│ metric_heuristic_*  │    │ independent_labeler   │
└────────┬────────────┘    └──────────┬───────────┘
         │ SemanticEvents             │ GroundTruthLabels
         │                            │
         └────────────┬───────────────┘
                      ▼
            ┌─────────────────────┐
            │ Evaluation harness   │
            │ PAR, FPR, FNR, MC    │
            │ leakage (dual-spec)  │
            └─────────────────────┘
                      │
                      ▼
            Pipeline (optional path)
            B5_full = align(pipeline_events, GT)
```

**Invariant D1:** `event_generator` MUST NOT import or load `experiments/ground_truth/rules/`.

**Invariant D2:** `independent_labeler` MUST NOT import or load `experiments/simulator/emission_profiles/`.

**Invariant D3:** Pipeline modules MUST NOT read GT at runtime.

**Invariant D4:** Leakage audit MUST extract emitter specs from emission profiles, not GT YAML.

### 2.3 Event generator (new behaviour)

Replace rule-driven emission as **primary** path with **metric-heuristic emission**:

- Per-scenario YAML in `experiments/simulator/emission_profiles/{scenario}.yaml`.
- Fields: label vocabulary (must overlap GT **label set** but not **rule predicates**), thresholds, hysteresis, false-alarm rate, miss rate, modality mapping.
- Emission is a **stochastic function** of world metrics: `SemanticEvent ~ Emit(world_state, seed, profile)` with deterministic PRNG substream per `(scenario, seed, tick, zone)`.

Shared **vocabulary** (same `semantic_label` strings) is allowed; shared **decision boundaries** are not.

### 2.4 Ground-truth oracle (unchanged role, clarified semantics)

- Continues to use `experiments/ground_truth/rules/`.
- Produces `ScenarioGroundTruth` via `build_independent_ground_truth(scenario, seed)`.
- Interpretation: **procedural reference** for what *should have been observed* given world truth, not what the emitter is specified to produce.

### 2.5 Evaluation harness extensions

| Mode | Command (proposed) | Purpose |
|------|-------------------|---------|
| Primary | `validate-tsgg --benchmark decoupled` (default after repair) | PAR, FPR, FNR, CI |
| Regression | `validate-tsgg --benchmark shared-spec` | Legacy rule-driven path |
| Stress | `leakage-audit --perturbation-grid` | MC robustness |

Harness outputs:

- `results/benchmark_decoupled/summary.json`
- `results_reference/benchmark_decoupled/` (pinned)
- Updated LaTeX tables (PAR, not 6× Pass)

---

## 3. Alternative architectures compared

### 3.A Independent emission profiles (recommended primary)

**Description:** GT rules frozen; emitter uses separate YAML profiles with different thresholds, timing, and noise.

| Criterion | Assessment |
|-----------|------------|
| **Scientific credibility** | **High.** Models realistic detector/pipeline mismatch; GT acts as external reference. |
| **Implementation complexity** | **Medium** (2–3 weeks). New profile schema, heuristic emitter, update spec_extraction, recalibrate profiles for target PAR band. |
| **Reproducibility impact** | **Low.** Deterministic given manifest hashes + seeds. |
| **Reviewer perception** | **Favourable.** “Authors separated observation model from evaluation oracle.” |
| **Risks** | Profile tuning could look like “inverse fitting” to hit PAR band — mitigate with **pre-registered profiles** in manifest before results. |

### 3.B Held-out ground-truth specifications

**Description:** Split GT rules into `rules_train/` (calibration) and `rules_eval/` (reporting). Emitter never sees eval rules; eval labels use held-out subset only.

| Criterion | Assessment |
|-----------|------------|
| **Scientific credibility** | **Medium–high** for ML-style eval; **medium** here because world is deterministic and small. |
| **Implementation complexity** | **Medium–high.** Rule splits, scenario coverage checks, dual leakage reports. |
| **Reproducibility impact** | **Medium.** More moving parts; manifest must pin both splits. |
| **Reviewer perception** | **Mixed.** Positive if split is by rule *family*; suspicious if split feels arbitrary on six scenarios. |
| **Risks** | Small scenario count → held-out set may be thin; easy to attack as “six scenarios, three eval rules.” |

**Recommended use:** **Supplementary** stress benchmark, not sole primary.

### 3.C Oracle-based ground truth

**Description:** GT derived from a **perfect observer** function of world state (e.g., direct threshold on raw metrics with oracle-specific logic), separate from both emitter profiles and authored YAML rules.

| Criterion | Assessment |
|-----------|------------|
| **Scientific credibility** | **High** as upper bound / sanity check; **low** as sole GT (oracle may not match procedural claims). |
| **Implementation complexity** | **Low–medium.** New `oracle_labeler.py` with documented deterministic functions. |
| **Reproducibility impact** | **Low.** |
| **Reviewer perception** | “Why two GTs?” unless roles are clearly separated (procedural vs oracle). |
| **Risks** | Shifts paper claims from “procedural GT” to “metric oracle”; may conflict with E2 leakage narrative. |

**Recommended use:** **Diagnostic / supplementary** (report agreement vs procedural GT and vs oracle GT).

### 3.D Comparison summary

| Alternative | Credibility | Effort | Primary? |
|-------------|-------------|--------|----------|
| A — Independent emission profiles | ★★★★☆ | Medium | **Yes** |
| B — Held-out GT specs | ★★★☆☆ | Medium–high | Supplementary |
| C — Oracle GT | ★★★☆☆ (role-dependent) | Low–medium | Diagnostic |

---

## 4. Recommended architecture

**Primary (reported in manuscript):** **3.A Independent emission profiles**

**Secondary:**

- **3.B** on a fixed held-out rule subset (`rules_eval/`) — one table in appendix.
- **3.C** oracle upper bound — one paragraph + optional table.

**Deprecated as headline metric:** shared-spec rule-driven 6/6 Pass.

**Retained as regression lane:** shared-spec mode behind `--benchmark shared-spec` for Phase-1 regression detection (not paper headline).

---

## 5. Primary metrics (formal definitions)

### 5.1 Event key space

For each tick emission or label:

\[
k = (\text{zone\_id}, \text{semantic\_label})
\]

Let \(P\) be multiset of predicted keys from evaluated event set (simulator-only or full pipeline after `events_for_b5_alignment`), and \(G\) from ground-truth oracle.

### 5.2 Procedural Agreement Rate (PAR)

Per run \((s, \sigma)\) (scenario \(s\), seed \(\sigma\)):

\[
\text{TP} = \sum_{k} \min(P(k), G(k)), \quad
\text{FP} = \sum_{k} \max(0, P(k) - G(k)), \quad
\text{FN} = \sum_{k} \max(0, G(k) - P(k))
\]

\[
\text{PAR}_{s,\sigma} = \frac{\text{TP}}{\text{TP} + \text{FP} + \text{FN}}
\]

(If \(\text{TP}+\text{FP}+\text{FN}=0\), define PAR = 1.0 and flag `empty_run`.)

**Aggregate PAR** (primary reported scalar):

\[
\overline{\text{PAR}} = \frac{1}{|S| \cdot |\Sigma|} \sum_{s \in S} \sum_{\sigma \in \Sigma} \text{PAR}_{s,\sigma}
\]

### 5.3 False positive rate (FPR)

\[
\text{FPR}_{s,\sigma} = \frac{\text{FP}}{\text{FP} + \text{TP}}
\]

If \(\text{FP}+\text{TP}=0\), define FPR = 0.

**Aggregate:**

\[
\overline{\text{FPR}} = \frac{\sum \text{FP}}{\sum (\text{FP} + \text{TP})}
\]

(micro-averaged over all event predictions.)

### 5.4 False negative rate (FNR)

\[
\text{FNR}_{s,\sigma} = \frac{\text{FN}}{\text{FN} + \text{TP}}
\]

If \(\text{FN}+\text{TP}=0\), define FNR = 0.

**Aggregate (micro):**

\[
\overline{\text{FNR}} = \frac{\sum \text{FN}}{\sum (\text{FN} + \text{TP})}
\]

### 5.5 Confidence intervals (bootstrap over seeds)

For each scenario \(s\), seeds \(\Sigma = \{\sigma_1,\ldots,\sigma_N\}\):

1. Compute \(\text{PAR}_{s,\sigma_i}\) for \(i=1..N\).
2. Bootstrap \(B=10{,}000\) resamples with replacement from \(\{\text{PAR}_{s,\sigma_i}\}\).
3. Report percentile 95% CI:

\[
\text{CI}_{95\%}(s) = \left[ Q_{2.5\%}(\text{PAR}_s^*), Q_{97.5\%}(\text{PAR}_s^*) \right]
\]

**Global CI:** bootstrap over pooled \(|S|\cdot N\) run-level PAR values.

Report in tables as: \(\overline{\text{PAR}} = 0.84 \; [0.81, 0.87]\) (example).

### 5.6 Robustness under threshold perturbation (RTP)

Extend existing MC in `leakage_audit/monte_carlo.py`:

For perturbation \(j = 1..N_{\mathrm{MC}}\), scale GT rule thresholds by \(\delta_j \sim U(0.88, 1.12)\), **emitter profile fixed** (seed fixed):

\[
\text{AgreementDrift}_j = 1 - \text{PAR}^{(j)}
\]

\[
\overline{\text{RTP}} = 1 - \frac{1}{N_{\mathrm{MC}}} \sum_j \text{AgreementDrift}_j
\]

Report alongside GT stability (existing) and **emitter stability** (should remain ≈ 1.0 under GT perturbation when emitter spec is fixed).

### 5.7 Leakage score (revised interpretation)

Same formula for \(L_S\), but **post-repair expectation**:

- `shared_variables_ratio` remains 1.0 (shared world — acceptable).
- `shared_threshold_ratio` should **drop** (target < 0.25).
- \(L_S\) target band: **0.30–0.50** (lower is stronger evidence of spec decoupling).

Disclosure quote (unchanged in spirit):

> This benchmark is procedurally independent but not distributionally independent.

Add:

> Event emission profiles and ground-truth rule specifications are distinct artefacts with pre-registered hashes.

### 5.8 What NOT to use as headline

| Deprecated headline | Replacement |
|--------------------|-------------|
| Pass/Fail per scenario from mean accuracy = 1.0 | PAR per scenario + CI |
| “6/6 Pass conformance” | “\(\overline{\text{PAR}} = X\) across six scenarios, \(N=30\) seeds” |
| Perfect FPR/FNR = 0 | Report non-zero rates explicitly |

---

## 6. Credible target ranges

These ranges define **acceptance criteria for profile calibration** (not post-hoc tuning to published results).

| Metric | Target range | Rationale |
|--------|--------------|-----------|
| \(\overline{\text{PAR}}\) (simulator vs procedural GT) | **0.78 – 0.92** | Strong but imperfect agreement |
| \(\overline{\text{PAR}}\) (full pipeline B5) | **0.72 – 0.88** | Pipeline adds fusion noise |
| \(\overline{\text{FPR}}\) | **0.04 – 0.18** | Observable false alarms |
| \(\overline{\text{FNR}}\) | **0.06 – 0.22** | Missed procedural labels |
| Per-scenario PAR min | **≥ 0.65** | No scenario collapses to trivial fail |
| \(L_S\) | **0.30 – 0.50** | Reduced threshold sharing |
| `shared_threshold_ratio` | **≤ 0.25** | Spec decoupling visible in audit |
| \(\overline{\text{RTP}}\) (MC) | **≥ 0.75** | GT perturbation does not collapse agreement |

### Why lower honest scores beat perfect scores

1. **Perfect agreement under shared rules** is logically equivalent to testing `emitter == labeler` — it carries **zero falsifiability**.
2. **Non-zero FP/FN** demonstrate the benchmark can penalize mismatch (architecture/harness sensitivity).
3. Reviewers trust **pre-registered imperfection** more than **post-hoc perfection** paired with \(L_S=0.575\).
4. For JSS, the claim is **software trace validation under synthetic coupling**, not detector optimality — PAR in the 0.8 band supports “implementable with disclosed gaps.”

---

## 7. Backward compatibility

### 7.1 Artifact commands

| Command | Post-repair behaviour |
|---------|----------------------|
| `bash artifact/commands.sh` | Runs **decoupled** benchmark by default; includes shared-spec regression lane |
| `validate-tsgg` | Default: decoupled; flag `--benchmark shared-spec` for legacy |
| `leakage-audit --fast` | Reports **dual-spec** overlap (primary) + legacy shared-spec (appendix) |
| `export-harness-b5-labels` | Exports **PAR table**, not Pass/Fail |
| `audit-comparison` | Unchanged (orthogonal to B5 repair) |

### 7.2 Reference outputs

| Path | Treatment |
|------|-----------|
| `results_reference/baseline_comparison/` | **Regenerate** with decoupled PAR |
| `results_reference/tables/harness_b5_by_scenario.tex` | **Replace** with PAR+CI table |
| `results_reference/leakage_audit/` | **Regenerate** (expect lower \(L_S\)) |
| Phase-1 perfect B5 outputs | **Archive** to `results_reference/regression/shared_spec/` |

### 7.3 Tests

| Test class | Treatment |
|------------|-----------|
| `test_emitter_matches_independent_labeler_keys_*` | **Move** to `tests/regression/shared_spec/` — expects equality |
| New `test_decoupled_emitter_bounded_agreement_*` | **Primary** — expects PAR ∈ target band |
| `test_independent_ground_truth.py` | Keep — tests oracle, not agreement |
| Audit comparison tests | Unchanged |

### 7.4 Benchmark tiers

| Tier | Name | Mode | Paper visibility |
|------|------|------|------------------|
| **Primary** | Decoupled conformance | Independent emission profiles | Main results |
| **Regression** | Shared-spec alignment | Rule-driven emitter + GT YAML | Appendix / regression only |
| **Supplementary** | Held-out GT / oracle | Alternatives B and C | Appendix |
| **Orthogonal** | Audit comparison | A1–A7 cross-format | Main results (unchanged) |

---

## 8. Benchmark manifest specification

**Path:** `experiments/benchmark_manifest.yaml`

### 8.1 Schema (normative)

```yaml
manifest_version: "benchmark_manifest_v1"
generated_for_release: "1.0.5"  # bump on repair merge
description: >
  Pre-registered benchmark artefacts for decoupled conformance evaluation.
  Hashes are SHA-256 of file contents (UTF-8, LF normalized).

benchmark_modes:
  primary:
    id: decoupled
    event_generator: metric_heuristic_emitter
    ground_truth: procedural_rules
  regression:
    id: shared_spec
    event_generator: rule_driven_emitter
    ground_truth: procedural_rules
  supplementary:
    - id: held_out_gt
    - id: oracle_gt

scenarios:
  - normal_flow
  - exit_blockage
  - multimodal_conflict
  - evacuation_recommendation
  - crowd_acceleration
  - audio_stress_signal

seeds:
  evaluation: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
               11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
               21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
  calibration: [101, 102, 103, 104, 105]  # profile tuning only; not headline seeds

artefact_hashes:
  ground_truth_rules:
    version: gt_rules_v1
    files:
      - path: experiments/ground_truth/rules/normal_flow.yaml
        sha256: "<computed>"
      # ... one entry per scenario rule file
  emission_profiles:
    version: emit_profiles_v1
    files:
      - path: experiments/simulator/emission_profiles/normal_flow.yaml
        sha256: "<computed>"
      # ... one entry per scenario profile
  audit_mutations:
    version: audit_mutations_v1
    path: experiments/audit_spec/mutations.yaml
    sha256: "<computed>"
  audit_tasks:
    version: audit_tasks_v1
    path: experiments/audit_spec/tasks.yaml
    sha256: "<computed>"

calibration_policy:
  description: >
    Emission profiles calibrated on calibration seeds only.
    Evaluation seeds frozen before profile freeze.
  target_par_band: [0.78, 0.92]
  target_fpr_band: [0.04, 0.18]
  target_fnr_band: [0.06, 0.22]

monte_carlo:
  n_perturbations: 50
  threshold_scale_range: [0.88, 1.12]
  bootstrap_resamples: 10000
  confidence_level: 0.95

leakage_audit:
  components: [world_dynamics, event_generator, ground_truth_rules]
  disclosure: >
    This benchmark is procedurally independent but not distributionally independent.
  expect_shared_variables_ratio: 1.0
  expect_shared_threshold_ratio_max: 0.25

reproducibility:
  python: ">=3.12"
  entrypoint: bash artifact/commands.sh
  pin_command: python -m dualexis.cli experiment verify-benchmark-manifest
  container: artifact/Dockerfile

provenance:
  authorship: TSGG reference implementation maintainers
  preregistration_date: "YYYY-MM-DD"  # date profiles frozen
  changelog: docs/benchmark_repair_design.md
```

### 8.2 Verification command (future)

```bash
python -m dualexis.cli experiment verify-benchmark-manifest
```

Fails CI if on-disk hashes ≠ manifest (tamper detection).

---

## 9. Manuscript changes

### 9.1 Abstract

**Remove:** “conforming to all six procedural scenarios” / “6/6 Pass” / implied perfect detection.

**Add:**

- Decoupled emission profiles vs procedural ground-truth oracle.
- Primary metric: \(\overline{\text{PAR}}\) with 95% CI, FPR, FNR.
- Transparent coupling: \(L_S\) with reduced threshold sharing post-repair.
- Retain audit-comparison and non-claims (no operational safety).

**Example sentence:**

> Procedural agreement between decoupled simulator emissions and an independent rule oracle averages \(\overline{\text{PAR}=0.XX}\) \([0.XX, 0.XX]\) across six scenarios and 30 seeds, with non-zero false-positive and false-negative rates disclosed.

### 9.2 Results

| Current artefact | Change |
|------------------|--------|
| Table 8 (Pass/Fail) | **Replace** with Table: scenario × \(\overline{\text{PAR}}\) × CI × FPR × FNR |
| Table 7 (leakage) | Update \(L_S\), `shared_threshold_ratio`; footnote on dual-spec |
| Harness honesty | PAR summary replaces implicit “Pass” narrative |
| New small table | Shared-spec regression (appendix): accuracy=1.0 labelled “implementation regression only” |

**New paragraph (results):**

Explain that perfect shared-spec agreement is retained as a **regression check**, not empirical validation.

### 9.3 Threats to validity

**Add paragraphs:**

1. **Conformance benchmark coupling (repaired):** emission profiles and GT rules are distinct; remaining coupling is world-dynamics shared variables (\(r_{\mathrm{vars}}=1\)).
2. **Profile calibration risk:** profiles tuned on held-out calibration seeds; manifest hashes pre-registered.
3. **Synthetic-only:** PAR bounds do not imply field detection accuracy.

**Revise:**

- Remove/improve language suggesting procedural independence implied distributional independence.

### 9.4 Table change summary

| Label | Old | New |
|-------|-----|-----|
| `tab:harness-b5-by-scenario` | Pass/Fail | `tab:procedural-agreement-by-scenario` (PAR, CI) |
| `tab:leakage-audit` | \(L_S=0.575\) high coupling | Updated \(L_S\), emphasize threshold decoupling |
| (new) `tab:shared-spec-regression` | — | Appendix only |
| `tab:audit-comparison` | Unchanged | Unchanged |

### 9.5 Contributions C3/C4 wording

- C3: “decoupled procedural conformance benchmark” not “six Pass labels.”
- C4: “reference implementation achieves bounded PAR under disclosed coupling.”

---

## 10. Implementation phases (reference, not in scope)

| Phase | Deliverable | Duration |
|-------|-------------|----------|
| A | Emission profiles + heuristic emitter + manifest | 2–3 weeks |
| B | Harness PAR/CI + regenerate reference outputs | 1 week |
| C | Manuscript + artifact docs | 1 week |
| D | Supplementary held-out / oracle (optional) | 1–2 weeks |

---

## 11. Hostile JSS reviewer assessment

**Reviewer comment (simulated):**

> “You fixed Phase 1 by making the emitter read the same YAML as the labeler, then reported 100% accuracy. Your leakage score admits coupling. Your audit comparison uses author-written baselines and author-written queries. This is self-validation dressed as evaluation.”

**Response enabled by this design:**

1. **Spec separation** with manifest hashes — auditable, not rhetorical.
2. **PAR < 1** with non-zero FP/FN — falsifiable benchmark.
3. **Lower \(L_S\)** on threshold overlap — quantitative evidence of decoupling.
4. **Shared-spec mode demoted** — authors concede prior circularity explicitly.
5. Audit comparison remains limited but **orthogonal** to B5 repair.

**Remaining attack surfaces:**

- Six scenarios still synthetic.
- Emission profiles may be tuned to hit PAR band (mitigated by preregistration + calibration seeds).
- World dynamics still shared (unavoidable; must disclose).
- Audit baselines still need PROV standardisation (separate track).

---

## 12. Coupling-controlled PAR decomposition (Phase E — diagnostic)

See **`docs/coupling_controlled_par.md`** for the coupling-controlled perturbation sweep (λ∈{0,0.25,0.5,0.75,1}, zone permutation / temporal desync / noise injection). This experiment tests whether decoupled PAR≈0.925 is explained by residual simulator coupling (H0) or retains measurable Δ_proc above a label-reassignment chance baseline PAR₀ (H1). **Diagnostic only** — not a new headline claim.

Command: `python -m dualexis.cli experiment coupling-controlled-par`

Outputs: `results_reference/coupling_controlled_par/`

---

## Final verdict

### Would this benchmark repair materially weaken the circularity criticism?

**Answer: Partially**

**Justification:**

- **Yes, materially**, for the specific criticism “emitter and labeler share procedural YAML → perfect B5 is tautological.” Independent emission profiles + PAR headline + reduced threshold overlap **directly dismantle** that logical chain.
- **Only partially**, because (i) shared world simulator keeps `shared_variables_ratio = 1.0`, (ii) six synthetic scenarios remain a single domain, (iii) profile calibration could be accused of hidden fitting unless manifest preregistration is enforced, and (iv) audit-comparison circularity is **unaffected** by this repair.

**Overall:** Moves the paper from **“likely Major Revision / reject on benchmark integrity”** to **“defensible JSS software-validation contribution with explicit limits”** — provided results are regenerated honestly and the manuscript stops headline-perfect conformance.

---

## References (repository)

| Path | Relevance |
|------|-----------|
| `dualexis/simulation/rule_driven_emitter.py` | Current shared-spec emitter |
| `dualexis/simulation/independent_labeler.py` | GT oracle |
| `dualexis/leakage_audit/spec_extraction.py` | Overlap extraction (must change) |
| `dualexis/evaluation/comparable_baselines.py` | B5 evaluation path |
| `dualexis/evaluation/metrics.py` | PAR/FPR/FNR definitions (extend) |
| `tests/unit/test_rule_driven_event_emission.py` | Tautology regression test |
| `experiments/ground_truth/rules/*.yaml` | Procedural GT specs |
| `artifact/commands.sh` | Reproduction entry point |

---

*End of design document.*
