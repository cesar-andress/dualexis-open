"""LaTeX export for formal governance state machine."""

from __future__ import annotations

from pathlib import Path

from dualexis.governance.formal_models import GovernanceAuditReport
from dualexis.governance.state_machine import transition_matrix_latex


def write_formal_governance_model_section(report: GovernanceAuditReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    m = report.metrics
    delta_tex = transition_matrix_latex()

    content = f"""\\subsection{{Formal Human-AI Governance State Machine}}
\\label{{sec:formal-governance-model}}

\\refimplname{{}} positions human oversight as a \\textbf{{formal governance framework for high-risk
decision support systems}}, not an informal review flag. The macro-state space is
\\begin{{equation*}}
  S = \\{{s^{{AI}}, s^{{H}}, s^{{I}}\\}}
\\end{{equation*}}
corresponding to \\emph{{AI recommendation}}, \\emph{{human review}}, and
\\emph{{institutional escalation}} phases. The transition alphabet is
$\\Sigma = \\{{\\mathrm{{issue}}, \\mathrm{{accept}}, \\mathrm{{override}}, \\mathrm{{dismiss}},
\\mathrm{{escalate}}, \\mathrm{{close}}\\}}$.

\\paragraph{{Transition function.}}
The deterministic transition function $\\delta: S \\times \\Sigma \\rightarrow S$ is
defined on the documented domain by:
{delta_tex}
High-severity recommendations initialise at $s^{{AI}}$.
Transition $\\tau_{{\\mathrm{{issue}}}}$ moves the artefact to $s^{{H}}$ when
$\\mathrm{{requires\\_human\\_review}}(s)$ holds.
Escalation $\\sigma=\\mathrm{{escalate}}$ maps to $s^{{I}}$ for institutional disposition.

\\paragraph{{Governance graph.}}
The empirical \\texttt{{GovernanceGraph}} $G=(V,E)$ aggregates simulated traces:
$|V|=3$ macro states, weighted edges $(s,\\sigma,s')$ with estimated
$\\hat{{P}}(s' \\mid s,\\sigma)$ from $N={report.trace_count}$ balanced-profile decisions.
The Graphviz artefact \\path{{results/governance/formal/formal_governance_graph.dot}}
visualises the machine.

\\paragraph{{Formal audit metrics.}}
The \\texttt{{GovernanceAuditReport}} bundles (same values as
$\\gamma_{{\\mathrm{{comp}}}}$ and $\\tau_{{\\mathrm{{trace}}}}$ in
Table~\\ref{{tab:harness-honesty}}):
\\begin{{itemize}}[noitemsep]
  \\item $\\gamma_{{\\mathrm{{comp}}}}$ (\\texttt{{governance\\_compliance\\_score}}) $={m.governance_compliance_score:.3f}$
        --- policy-aligned terminal states;
  \\item \\textbf{{institutional\\_reliance\\_index}} $={m.institutional_reliance_index:.3f}$
        --- appropriate escalation when required;
  \\item \\textbf{{human\\_override\\_resilience}} $={m.human_override_resilience:.3f}$
        --- corrective overrides when AI advice is incorrect;
  \\item $\\tau_{{\\mathrm{{trace}}}}$ (\\texttt{{decision\\_traceability}}) $={m.decision_traceability:.3f}$
        --- complete $(s^{{AI}} \\rightarrow s^{{H}} \\rightarrow s^{{\\cdot}})$ audit chains.
\\end{{itemize}}

\\paragraph{{Positioning.}}
This FSM separates \\emph{{advisory automation}} (L4--L5) from \\emph{{accountable disposition}}
(L6), enabling institutions to audit compliance, escalation discipline, and trace completeness
before pilot deployment. Metrics are synthetic; the contribution is the \\textbf{{explicit
governance state machine}} and trace schema, not field outcome claims.
"""
    path.write_text(content, encoding="utf-8")


__all__ = ["write_formal_governance_model_section"]
