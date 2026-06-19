# Coupling-controlled PAR decomposition

Diagnostic experiment only. Not primary conformance evidence.

## Purpose

Test whether decoupled PAR≈0.925 is explained mainly by residual simulator coupling (H0) or
whether measurable procedural agreement remains after destroying shared input structure (H1).

## Design

- Ground-truth oracle always uses **clean** simulator variables.
- Metric-heuristic emitter sees **perturbed** variables controlled by λ∈{0,0.25,0.5,0.75,1}.
- λ=0 reproduces the default decoupled benchmark path (zone-permutation channel).
- λ=1 maximally destroys shared structure for the active channel.

### Channels

1. **zone_permutation** — shuffle zone identities; preserve marginal metric values.
2. **temporal_desync** — feed lagged tick metrics to the emitter.
3. **noise_injection** — add scaled noise to emitter-visible variables.

### Metrics

- PAR, FPR, FNR with 95% bootstrap CI
- PAR₀ — chance baseline from 1000 random **label reassignments** per run (zone keys fixed)
- Δ_proc = PAR − PAR₀ with 95% bootstrap CI
- Retained coupling proxy — Pearson correlation between clean and emitter-visible zone metrics

### Hypotheses

- **H0 (coupling-explained):** PAR(λ=1) ≈ PAR₀; Δ_proc(λ=1) CI includes 0.
- **H1 (residual procedural agreement):** PAR(λ=1) > PAR₀; Δ_proc(λ=1) CI excludes 0.

## Commands

```bash
python -m dualexis.cli experiment coupling-controlled-par
python -m dualexis.cli experiment coupling-controlled-par --output results_reference/coupling_controlled_par
```

## Outputs

- `results_reference/coupling_controlled_par/coupling_controlled_par.csv`
- `results_reference/coupling_controlled_par/coupling_controlled_par.json`
- `results_reference/coupling_controlled_par/coupling_controlled_par.tex`
- `results_reference/coupling_controlled_par/coupling_controlled_par_by_run.csv`

## Constraints

- Does not modify TSGG architecture, frozen GT rules, or emission profiles.
- Does not replace the primary decoupled benchmark tables.
- No operational safety or deployment validity claims.
