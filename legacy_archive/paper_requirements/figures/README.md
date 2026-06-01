# Institutional diagrams (DUALEXIS pilot requirements)

Governance-oriented figures for `paper_requirements/main.pdf`.

## LaTeX (recommended for PDF)

| Figure | Source | Label |
|--------|--------|-------|
| Human-in-the-loop flow | `fig_governance_hitl_flow.tex` | `fig:governance-hitl-flow` |
| Pilot phase roadmap | `fig_pilot_phase_roadmap.tex` | `fig:pilot-phase-roadmap` |
| Privacy architecture | `fig_privacy_architecture_overview.tex` | `fig:privacy-architecture-overview` |
| Governance oversight | `fig_governance_oversight_model.tex` | `fig:governance-oversight-model` |

Included via `sections/institutional_diagrams.tex`.

## Mermaid (editable concepts)

Parallel `.mmd` sources for slides and Horizon annexes. Render with:

```bash
npx @mermaid-js/mermaid-cli -i governance_hitl_flow.mmd -o governance_hitl_flow.pdf -b white
```

Style: monochrome, minimal, no engineering port lists.
