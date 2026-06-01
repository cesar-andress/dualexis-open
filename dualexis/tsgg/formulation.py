"""Unified TSGG mathematical formulation (LaTeX)."""

from __future__ import annotations

from dualexis.tsgg.models import TsggUnifiedMetrics


def build_tsgg_formulation_block(metrics: TsggUnifiedMetrics) -> str:
    """Return the canonical TSGG equation block for paper export."""
    return f"""\\begin{{equation}}
  \\label{{eq:tsgg-pipeline}}
  \\Phi_{{\\mathrm{{TSGG}}}}:
  \\; E \\xrightarrow{{\\rho}} S \\xrightarrow{{\\kappa}} C \\xrightarrow{{\\omega}} R
  \\xrightarrow{{\\delta}} G \\xrightarrow{{\\alpha}} A
\\end{{equation}}
where $E$ is a multiset of privacy-bounded evidence records, $S$ a zone-indexed safety-state
trajectory, $C$ causal transitions with typed factors
$(\\texttt{{contributes\\_to}}, \\texttt{{aggravates}}, \\texttt{{mitigates}}, \\texttt{{triggers}})$,
$R$ orchestration recommendations, $G$ macro governance decisions over
$S_{{\\mathrm{{gov}}}}=\\{{s^{{AI}}, s^{{H}}, s^{{I}}\\}}$, and $A$ an append-only audit trace.

\\begin{{equation}}
  \\label{{eq:tsgg-trust}}
  \\mathcal{{I}}_{{\\mathrm{{TSGG}}}} =
  0.30\\,\\bar{{P}}_{{\\mathrm{{st}}}} +
  0.25\\,\\Pi_{{\\mathrm{{causal}}}} +
  0.25\\,\\bigl(0.5\\,\\pi_{{\\mathrm{{proc}}}} + 0.5\\,\\pi_{{\\mathrm{{dist}}}}\\bigr)(1 - L_S) +
  0.20\\,\\bar{{P}}_{{\\mathrm{{gov}}}}
\\end{{equation}}
with $\\bar{{P}}_{{\\mathrm{{st}}}}=(P_{{\\mathrm{{prec}}}}+P_{{\\mathrm{{rec}}}})/2$,
$\\Pi_{{\\mathrm{{causal}}}}$ causal-path completeness, $L_S\\in[0,1]$ the leakage score,
$\\pi_{{\\mathrm{{proc}}}},\\pi_{{\\mathrm{{dist}}}}$ procedural and distributional independence,
and $\\bar{{P}}_{{\\mathrm{{gov}}}}=(\\gamma_{{\\mathrm{{comp}}}}+\\tau_{{\\mathrm{{trace}}}})/2$.
Synthetic harness evaluation yields
$\\mathcal{{I}}_{{\\mathrm{{TSGG}}}}={metrics.tsgg_trust_index:.3f}$.
"""


__all__ = ["build_tsgg_formulation_block"]
