# DUALEXIS publication diagrams

Publication-quality Mermaid sources for the paper and documentation.
Sources live in this directory; mirrored copies are kept in `paper/figures/`.

## Build (PDF / SVG for LaTeX)

From the repository root:

```bash
./scripts/render_diagrams.sh
```

Requires Node.js (`npx @mermaid-js/mermaid-cli`). Outputs:

| Diagram | PDF / SVG basename |
| ------- | ------------------ |
| End-to-end pipeline | `end_to_end_pipeline` |
| Privacy runtime | `privacy_runtime` |
| Temporal safety graph | `temporal_safety_graph` |
| Edge deployment | `edge_deployment_architecture` |
| Human-in-the-loop flow | `hitl_orchestration_flow` |
| Evaluation workflow | `experimental_evaluation_workflow` |

## LaTeX includes

Individual figure wrappers are in `paper/figures/fig_*.tex`.
Include in a section file, for example:

```latex
\input{figures/fig_end_to_end_pipeline}
```

Or include all figures (draft builds):

```latex
\input{figures/includes}
```

Compile the paper from `paper/` after rendering PDFs.

## Markdown embeds

Use fenced `mermaid` blocks in GitHub, GitLab, MkDocs Material, or VS Code preview.
Full copy-paste blocks: [`embeds.md`](embeds.md).

Quick reference:

| Topic | Source | Docs |
| ----- | ------ | ---- |
| Pipeline | [`end_to_end_pipeline.mmd`](end_to_end_pipeline.mmd) | [pipeline.md](../pipeline.md) |
| Privacy runtime | [`privacy_runtime.mmd`](privacy_runtime.mmd) | [privacy.md](../privacy.md) |
| Temporal graph | [`temporal_safety_graph.mmd`](temporal_safety_graph.mmd) | [temporal_graph.md](../temporal_graph.md) |
| Edge deployment | [`edge_deployment_architecture.mmd`](edge_deployment_architecture.mmd) | [edge_runtime.md](../edge_runtime.md) |
| HITL orchestration | [`hitl_orchestration_flow.mmd`](hitl_orchestration_flow.mmd) | [framework.md](../framework.md) |
| Evaluation | [`experimental_evaluation_workflow.mmd`](experimental_evaluation_workflow.mmd) | [evaluation.md](../evaluation.md) |

Shared theme snippet: [`_mermaid_theme.mmd`](_mermaid_theme.mmd).

## Styling

Diagrams use the Mermaid `neutral` theme with consistent spacing, curved edges,
and semantic color classes (privacy gates, layer nodes, I/O). Edit the `%%{init: ...}%%`
block at the top of each `.mmd` file to adjust typography for print.
