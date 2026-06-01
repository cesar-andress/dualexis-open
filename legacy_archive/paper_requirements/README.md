# DUALEXIS Deployment and Governance Requirements

Stakeholder circulation pack for school pilots (UCJC/SEK, DPOs, ethics committees, Horizon Europe).

**Document ID:** `DUALEXIS-REQ-2026-001` · **Version:** 0.5

## Build

```bash
cd paper_requirements
make all          # main.pdf + executive_brief.pdf
make pdf          # requirements body only
make executive    # executive brief only
make check        # structure check (no LaTeX required)
```

## Outputs

| PDF | Audience | Pages (approx.) |
| --- | -------- | ----------------- |
| `executive_brief.pdf` | Leadership, ethics boards, parents (summary), non-technical stakeholders | 6–8 |
| `main.pdf` | DPO, safety, IT, operational planning, Horizon partners | 25–28 |

## Circulation order (recommended)

1. **Executive Brief** → leadership, DPO, ethics committee  
2. **Steering workshop** → Box 1, pause/stop rights, co-design  
3. **Protocol-mapping workshop** → Appendix A templates  
4. **Full requirements body** → safety, IT (when engaged), consortium governance leads  
5. **Appendix E (hardware BOM)** → IT and procurement only  

See **Section: Institutional Circulation and Workshop Guide** in `main.pdf`.

## Main document structure

1. How to use this pack + HITL diagram  
2. Box 1 — boundaries and exclusions  
3. School context, use cases, objectives  
4. Local processing, operational layout, and **procurement-grade hardware tiers (A/B/C)**  
5. Privacy, GDPR, AI Act, and **full DPIA checklist (15 items)**  
6. Operational protocols (SOP, **mandatory tabletop**, training)  
7. Pilot programme (phases, timeline, RACI, **go/no-go**, **stop conditions**, co-design / opt-out)  
8. **Institutional circulation and workshop guide** (routing, communications, objections)  
9. Evaluation and key risks (summary)  
10. Next steps by stakeholder  

**Appendices:** A Governance templates & workshop aids · B Budget · C Full risk register · D Technical diagrams + IT reference · **E Reference hardware BOM**

## Executive brief

Standalone summary: purpose, advisory/HITL model, pilot pathway, governance gates, co-design, FAQ, priority risks, and companion-document pointer.

## Status

Requirements and planning only — not legal certification, GDPR/AI Act conformity, or evidence of safety effectiveness.

## Related artifacts

- Framework paper: `paper/main.tex`  
- Full technical architecture (IT): `sections/appendix_technical_architecture.tex`  
- Institutional figures: `figures/`  
