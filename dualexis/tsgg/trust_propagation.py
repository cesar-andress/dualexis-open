"""Formal trust propagation over the TSGG pipeline.

Trust theory: each vertex v carries T(v) in [0,1]. Stage-specific update operators
compose parent trust with local confidence to yield a trust-aware reasoning graph.
"""

from __future__ import annotations

import json
import shutil
import statistics
import subprocess
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from dualexis.governance.formal_models import GovernanceDecisionTrace
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.orchestration.models import SeverityLevel
from dualexis.sssg.models import EvidenceRecord, SafetyState, StateSnapshotNode
from dualexis.cssg.models import CausalStateTransition
from dualexis.tsgg.models import TsggRunRecord


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


class TrustNodeKind(StrEnum):
    """TSGG vertex kinds for trust propagation."""

    EVIDENCE = "evidence"
    SAFETY_STATE = "safety_state"
    CAUSAL_TRANSITION = "causal_transition"
    RECOMMENDATION = "recommendation"
    GOVERNANCE_DECISION = "governance_decision"
    AUDIT_TRACE = "audit_trace"


class TrustNode(BaseModel):
    """Vertex v with trust label T(v)."""

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(min_length=1)
    kind: TrustNodeKind
    trust: float = Field(ge=0.0, le=1.0)
    parent_id: str | None = None
    operator: str = Field(min_length=1, max_length=64)
    metadata: dict[str, str | float | int] = Field(default_factory=dict)


class TrustPath(BaseModel):
    """A directed trust-bearing path pi through TSGG."""

    model_config = ConfigDict(frozen=True)

    path_id: str
    scenario_id: str
    seed: int
    node_ids: tuple[str, ...]
    path_trust: float = Field(ge=0.0, le=1.0)


class TrustPropagationMetrics(BaseModel):
    """Aggregate trust-theoretic descriptors."""

    model_config = ConfigDict(frozen=True)

    trust_consistency: float = Field(ge=0.0, le=1.0)
    trust_decay: float = Field(ge=0.0, le=1.0)
    trust_recovery: float = Field(ge=0.0, le=1.0)
    mean_node_trust: float = Field(ge=0.0, le=1.0)
    mean_path_trust: float = Field(ge=0.0, le=1.0)
    mean_recommendation_trust: float = Field(ge=0.0, le=1.0)


class TrustPropagationReport(BaseModel):
    """Trust propagation result for one or more TSGG runs."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    nodes: tuple[TrustNode, ...] = Field(default_factory=tuple)
    paths: tuple[TrustPath, ...] = Field(default_factory=tuple)
    node_trust: dict[str, float] = Field(default_factory=dict)
    path_trust: dict[str, float] = Field(default_factory=dict)
    recommendation_trust: dict[str, float] = Field(default_factory=dict)
    metrics: TrustPropagationMetrics
    benchmark_trust_prior: float = Field(ge=0.0, le=1.0, default=1.0)
    disclaimer: str = Field(min_length=1)


TRUST_PROPAGATION_DISCLAIMER = (
    "Trust propagation on synthetic TSGG traces. Operators define a compositional "
    "trust theory; values are feasibility descriptors, not calibrated field probabilities."
)

STAGE_ORDER: tuple[TrustNodeKind, ...] = (
    TrustNodeKind.EVIDENCE,
    TrustNodeKind.SAFETY_STATE,
    TrustNodeKind.CAUSAL_TRANSITION,
    TrustNodeKind.RECOMMENDATION,
    TrustNodeKind.GOVERNANCE_DECISION,
    TrustNodeKind.AUDIT_TRACE,
)


def evidence_reliability(evidence: EvidenceRecord, *, privacy_factor: float = 1.0) -> float:
    """rho: evidence reliability operator."""
    base = 0.78
    if evidence.metric_value is not None:
        base += 0.08
    if evidence.description:
        base += 0.04
    if evidence.kind.value == "semantic_event":
        base += 0.05
    return _clamp(base * privacy_factor)


def safety_state_confidence(snapshot: StateSnapshotNode) -> float:
    """sigma: safety-state confidence given snapshot semantics."""
    if snapshot.state == SafetyState.NORMAL:
        return 0.92
    if snapshot.state == SafetyState.EVACUATION_CANDIDATE:
        return 0.88
    return 0.90


def causal_confidence(transition: CausalStateTransition) -> float:
    """kappa: causal transition confidence from attribution strength."""
    factor_bonus = min(1.0, len(transition.causal_factors) / 3.0) * 0.15
    evidence_bonus = min(1.0, len(transition.supporting_evidence) / 2.0) * 0.1
    return _clamp(transition.confidence * (0.75 + factor_bonus + evidence_bonus))


def recommendation_confidence(
    *,
    severity: SeverityLevel,
    requires_human_review: bool,
    ai_correct: bool | None = None,
) -> float:
    """omega: recommendation trust from severity and oracle alignment when known."""
    base = {
        SeverityLevel.LOW: 0.82,
        SeverityLevel.MEDIUM: 0.78,
        SeverityLevel.HIGH: 0.72,
        SeverityLevel.CRITICAL: 0.68,
    }[severity]
    if requires_human_review:
        base *= 0.92
    if ai_correct is True:
        base = min(1.0, base + 0.08)
    elif ai_correct is False:
        base *= 0.75
    return _clamp(base)


def governance_confidence(trace: GovernanceDecisionTrace) -> float:
    """delta: governance decision confidence."""
    score = 0.70
    if trace.policy_compliant:
        score += 0.22
    if trace.trace_complete:
        score += 0.06
    if trace.requires_escalation and trace.terminal_macro_state.value == "institutional_escalation":
        score += 0.04
    return _clamp(score)


def audit_confidence(trace: GovernanceDecisionTrace) -> float:
    """alpha: audit-trace confidence."""
    steps = len(trace.steps)
    if steps < 2:
        return 0.55
    score = 0.85 + 0.05 * min(steps - 2, 2)
    if trace.trace_complete:
        score += 0.08
    return _clamp(score)


def compose_trust(parent_trust: float, local_confidence: float) -> float:
    """Psi: T(v) = T(parent) * phi_local (multiplicative propagation)."""
    return _clamp(parent_trust * local_confidence)


def benchmark_trust_prior(leakage: LeakageAuditReport | None) -> float:
    """Root prior pi_0 from benchmark independence (external trust boundary)."""
    if leakage is None:
        return 1.0
    independence = (
        0.5 * leakage.independence.procedural_independence
        + 0.5 * leakage.independence.distributional_independence
    )
    return _clamp(independence * (1.0 - leakage.leakage_score))


def propagate_trust_for_record(
    record: TsggRunRecord,
    *,
    benchmark_prior: float = 1.0,
    privacy_factor: float = 1.0,
) -> TrustPropagationReport:
    """Build trust-labelled nodes and paths for one TSGG execution."""
    nodes: list[TrustNode] = []
    paths: list[TrustPath] = []
    node_trust: dict[str, float] = {}
    recommendation_trust: dict[str, float] = {}

    gov_by_zone: dict[str, GovernanceDecisionTrace] = {}
    for trace in record.governance_traces:
        gov_by_zone.setdefault(trace.zone_id, trace)

    for transition in record.causal_trace.causal_transitions:
        path_nodes: list[TrustNode] = []
        parent_id: str | None = None
        parent_trust = benchmark_prior

        for evidence in transition.supporting_evidence:
            ev_id = f"ev:{record.scenario_id}:{record.seed}:{evidence.evidence_id}"
            local = evidence_reliability(evidence, privacy_factor=privacy_factor)
            trust = compose_trust(parent_trust, local) if parent_id else _clamp(local * benchmark_prior)
            node = TrustNode(
                node_id=ev_id,
                kind=TrustNodeKind.EVIDENCE,
                trust=trust,
                parent_id=parent_id,
                operator="rho_evidence_reliability",
                metadata={"zone_id": evidence.zone_id, "tick": evidence.tick},
            )
            path_nodes.append(node)
            nodes.append(node)
            node_trust[ev_id] = trust
            parent_id = ev_id
            parent_trust = trust

        snapshot = _snapshot_for_transition(record, transition)
        snap_id = f"ss:{transition.transition_id}"
        snap_local = safety_state_confidence(snapshot) if snapshot else 0.85
        snap_trust = compose_trust(parent_trust, snap_local)
        snap_node = TrustNode(
            node_id=snap_id,
            kind=TrustNodeKind.SAFETY_STATE,
            trust=snap_trust,
            parent_id=parent_id,
            operator="sigma_safety_state",
            metadata={"zone_id": transition.zone_id, "state": transition.to_state.value},
        )
        path_nodes.append(snap_node)
        nodes.append(snap_node)
        node_trust[snap_id] = snap_trust

        causal_id = f"ct:{transition.transition_id}"
        causal_local = causal_confidence(transition)
        causal_trust = compose_trust(snap_trust, causal_local)
        causal_node = TrustNode(
            node_id=causal_id,
            kind=TrustNodeKind.CAUSAL_TRANSITION,
            trust=causal_trust,
            parent_id=snap_id,
            operator="kappa_causal_confidence",
            metadata={"zone_id": transition.zone_id},
        )
        path_nodes.append(causal_node)
        nodes.append(causal_node)
        node_trust[causal_id] = causal_trust

        rec = _recommendation_for_zone(record, transition.zone_id)
        rec_id = f"rec:{rec.recommendation_id}" if rec else f"rec:orphan:{transition.transition_id}"
        ai_correct = None
        gov_trace = gov_by_zone.get(transition.zone_id)
        if gov_trace is not None:
            ai_correct = gov_trace.ai_correct
        rec_local = recommendation_confidence(
            severity=rec.severity if rec else SeverityLevel.MEDIUM,
            requires_human_review=rec.requires_human_review if rec else True,
            ai_correct=ai_correct,
        )
        rec_trust = compose_trust(causal_trust, rec_local)
        rec_node = TrustNode(
            node_id=rec_id,
            kind=TrustNodeKind.RECOMMENDATION,
            trust=rec_trust,
            parent_id=causal_id,
            operator="omega_recommendation",
        )
        path_nodes.append(rec_node)
        nodes.append(rec_node)
        node_trust[rec_id] = rec_trust
        if rec:
            recommendation_trust[str(rec.recommendation_id)] = rec_trust

        gov_trust = rec_trust
        audit_trust = rec_trust
        if gov_trace is not None:
            gov_node_id = f"gov:{gov_trace.trace_id}"
            gov_local = governance_confidence(gov_trace)
            gov_trust = compose_trust(rec_trust, gov_local)
            gov_node = TrustNode(
                node_id=gov_node_id,
                kind=TrustNodeKind.GOVERNANCE_DECISION,
                trust=gov_trust,
                parent_id=rec_id,
                operator="delta_governance",
                metadata={"policy_compliant": int(gov_trace.policy_compliant)},
            )
            path_nodes.append(gov_node)
            nodes.append(gov_node)
            node_trust[gov_node_id] = gov_trust

            audit_id = f"aud:{gov_trace.trace_id}"
            audit_local = audit_confidence(gov_trace)
            audit_trust = compose_trust(gov_trust, audit_local)
            audit_node = TrustNode(
                node_id=audit_id,
                kind=TrustNodeKind.AUDIT_TRACE,
                trust=audit_trust,
                parent_id=gov_node_id,
                operator="alpha_audit",
            )
            path_nodes.append(audit_node)
            nodes.append(audit_node)
            node_trust[audit_id] = audit_trust

        path_trust_val = path_nodes[-1].trust if path_nodes else 0.0
        path_id = f"path:{record.scenario_id}:{record.seed}:{transition.transition_id}"
        paths.append(
            TrustPath(
                path_id=path_id,
                scenario_id=record.scenario_id,
                seed=record.seed,
                node_ids=tuple(n.node_id for n in path_nodes),
                path_trust=path_trust_val,
            )
        )

    metrics = aggregate_trust_metrics(nodes, paths, recommendation_trust)
    return TrustPropagationReport(
        generated_at=datetime.now(tz=UTC),
        nodes=tuple(nodes),
        paths=tuple(paths),
        node_trust=node_trust,
        path_trust={path.path_id: path.path_trust for path in paths},
        recommendation_trust=recommendation_trust,
        metrics=metrics,
        benchmark_trust_prior=benchmark_prior,
        disclaimer=TRUST_PROPAGATION_DISCLAIMER,
    )


def propagate_trust_batch(
    records: list[TsggRunRecord],
    *,
    leakage: LeakageAuditReport | None = None,
) -> TrustPropagationReport:
    """Merge trust graphs from multiple TSGG runs."""
    prior = benchmark_trust_prior(leakage)
    privacy = prior
    partials = [
        propagate_trust_for_record(record, benchmark_prior=prior, privacy_factor=privacy)
        for record in records
    ]
    if not partials:
        empty_metrics = TrustPropagationMetrics(
            trust_consistency=1.0,
            trust_decay=0.0,
            trust_recovery=0.0,
            mean_node_trust=0.0,
            mean_path_trust=0.0,
            mean_recommendation_trust=0.0,
        )
        return TrustPropagationReport(
            generated_at=datetime.now(tz=UTC),
            metrics=empty_metrics,
            benchmark_trust_prior=prior,
            disclaimer=TRUST_PROPAGATION_DISCLAIMER,
        )

    all_nodes = [node for report in partials for node in report.nodes]
    all_paths = [path for report in partials for path in report.paths]
    rec_trust: dict[str, float] = {}
    node_trust: dict[str, float] = {}
    path_trust: dict[str, float] = {}
    for report in partials:
        node_trust.update(report.node_trust)
        path_trust.update(report.path_trust)
        rec_trust.update(report.recommendation_trust)

    metrics = aggregate_trust_metrics(all_nodes, all_paths, rec_trust)
    return TrustPropagationReport(
        generated_at=datetime.now(tz=UTC),
        nodes=tuple(all_nodes),
        paths=tuple(all_paths),
        node_trust=node_trust,
        path_trust=path_trust,
        recommendation_trust=rec_trust,
        metrics=metrics,
        benchmark_trust_prior=prior,
        disclaimer=TRUST_PROPAGATION_DISCLAIMER,
    )


def aggregate_trust_metrics(
    nodes: list[TrustNode],
    paths: list[TrustPath],
    recommendation_trust: dict[str, float],
) -> TrustPropagationMetrics:
    """Compute trust_consistency, trust_decay, trust_recovery."""
    if not nodes:
        return TrustPropagationMetrics(
            trust_consistency=1.0,
            trust_decay=0.0,
            trust_recovery=0.0,
            mean_node_trust=0.0,
            mean_path_trust=0.0,
            mean_recommendation_trust=0.0,
        )

    by_kind: dict[TrustNodeKind, list[float]] = {kind: [] for kind in STAGE_ORDER}
    for node in nodes:
        by_kind[node.kind].append(node.trust)

    stage_means = [statistics.mean(by_kind[kind]) for kind in STAGE_ORDER if by_kind[kind]]
    if len(stage_means) >= 2 and statistics.mean(stage_means) > 0:
        cv = statistics.pstdev(stage_means) / statistics.mean(stage_means)
        trust_consistency = _clamp(1.0 - cv)
    else:
        trust_consistency = 1.0

    decays: list[float] = []
    recoveries: list[float] = []
    for path in paths:
        if len(path.node_ids) < 2:
            continue
        trusts = [_node_trust_for_path(nodes, node_id) for node_id in path.node_ids]
        if trusts[0] > 0:
            decays.append(_clamp(1.0 - trusts[-1] / trusts[0]))
        rec_trust = _trust_at_kind(path, nodes, TrustNodeKind.RECOMMENDATION)
        gov_trust = _trust_at_kind(path, nodes, TrustNodeKind.GOVERNANCE_DECISION)
        if rec_trust is not None and gov_trust is not None and gov_trust > rec_trust:
            gap = 1.0 - rec_trust
            recoveries.append(_clamp((gov_trust - rec_trust) / gap if gap > 1e-6 else 0.0))

    trust_decay = round(statistics.mean(decays) if decays else 0.0, 4)
    trust_recovery = round(statistics.mean(recoveries) if recoveries else 0.0, 4)
    rec_values = list(recommendation_trust.values())

    return TrustPropagationMetrics(
        trust_consistency=trust_consistency,
        trust_decay=trust_decay,
        trust_recovery=trust_recovery,
        mean_node_trust=round(statistics.mean(n.trust for n in nodes), 4),
        mean_path_trust=round(statistics.mean(p.path_trust for p in paths) if paths else 0.0, 4),
        mean_recommendation_trust=round(
            statistics.mean(rec_values) if rec_values else 0.0, 4
        ),
    )


def _node_trust_for_path(nodes: list[TrustNode], node_id: str) -> float:
    for node in nodes:
        if node.node_id == node_id:
            return node.trust
    return 0.0


def _trust_at_kind(
    path: TrustPath,
    nodes: list[TrustNode],
    kind: TrustNodeKind,
) -> float | None:
    index = {node.node_id: node for node in nodes}
    for node_id in path.node_ids:
        node = index.get(node_id)
        if node is not None and node.kind == kind:
            return node.trust
    return None


def _snapshot_for_transition(
    record: TsggRunRecord,
    transition: CausalStateTransition,
) -> StateSnapshotNode | None:
    for snapshot in record.causal_trace.snapshots:
        if snapshot.zone_id == transition.zone_id and snapshot.tick == transition.tick:
            return snapshot
    for snapshot in reversed(record.causal_trace.snapshots):
        if snapshot.zone_id == transition.zone_id:
            return snapshot
    return None


def _recommendation_for_zone(record: TsggRunRecord, zone_id: str):
    for rec in record.pipeline_output.recommendations:
        if rec.target_zone_id == zone_id:
            return rec
    if record.pipeline_output.recommendations:
        return record.pipeline_output.recommendations[0]
    return None


def write_trust_propagation_section(report: TrustPropagationReport, path: Path) -> None:
    """LaTeX section for trust propagation theory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    m = report.metrics
    content = f"""\\section{{Trust propagation on TSGG}}
\\label{{sec:trust-propagation}}

TSGG is positioned as a \\textbf{{trust-aware reasoning graph}}: every vertex $v$ carries
a trust label $T(v)\\in[0,1]$, propagated along the pipeline by stage-specific update
operators rather than a single post-hoc composite score.

\\paragraph{{Trust labels.}}
Let $G=(V,E)$ be the TSGG instance for scenario $\\xi$ and seed $\\zeta$.
For $v\\in V$,
\\begin{{equation}}
  \\label{{eq:tsgg-trust-node}}
  T(v) \\in [0,1], \\qquad T(v_0) = \\pi_0,
\\end{{equation}}
where $\\pi_0$ is the \\emph{{benchmark trust prior}} from leakage independence
($\\pi_0={report.benchmark_trust_prior:.3f}$ in the current harness).

\\paragraph{{Update operators.}}
Multiplicative propagation composes parent trust with local confidence $\\phi$:
\\begin{{equation}}
  \\label{{eq:tsgg-trust-compose}}
  T(v) = \\Psi\\bigl(T(\\mathrm{{pa}}(v)),\\,\\phi(v)\\bigr)
  = T(\\mathrm{{pa}}(v))\\cdot \\phi(v),
\\end{{equation}}
with operators:
$\\rho$ \\emph{{evidence reliability}},
$\\sigma$ \\emph{{safety-state confidence}},
$\\kappa$ \\emph{{causal confidence}},
$\\omega$ \\emph{{recommendation confidence}},
$\\delta$ \\emph{{governance confidence}}, and
$\\alpha$ \\emph{{audit confidence}}.

\\paragraph{{Path trust.}}
For a directed path $\\pi=(v_1,\\ldots,v_k)$ with composed vertex trust as in
Equation~\\eqref{{eq:tsgg-trust-compose}}, path trust is the terminal label
\\begin{{equation}}
  \\label{{eq:tsgg-path-trust}}
  T(\\pi) = T(v_k).
\\end{{equation}}
(Local factors $\\phi(v_i)$ satisfy $T(v_i)=T(v_{{i-1}})\\cdot\\phi(v_i)$ along $\\pi$.)
Recommendation trust is $T(r)=T(\\pi_r)$ for the path $\\pi_r$ terminating at recommendation
vertex $r$ (mean $\\bar{{T}}_r={m.mean_recommendation_trust:.3f}$ over the audit sample).

\\paragraph{{Trust-theoretic metrics.}}
\\begin{{itemize}}[noitemsep]
  \\item \\textbf{{trust\\_consistency}} $={m.trust_consistency:.3f}$ --- low dispersion of
        mean stage trust (stable propagation profile);
  \\item \\textbf{{trust\\_decay}} $={m.trust_decay:.3f}$ --- average relative loss
        $1-T(v_k)/T(v_1)$ along audit paths;
  \\item \\textbf{{trust\\_recovery}} $={m.trust_recovery:.3f}$ --- governance-stage uplift
        when $T(g)>T(r)$ after low recommendation trust.
\\end{{itemize}}
Mean node trust $\\bar{{T}}_V={m.mean_node_trust:.3f}$;
mean path trust $\\bar{{T}}_\\pi={m.mean_path_trust:.3f}$.

\\input{{sections/trust_flow_figure}}
\\input{{tables/trust_propagation_metrics}}

\\paragraph{{Relation to $\\mathcal{{I}}_{{\\mathrm{{TSGG}}}}$.}}
The composite index in Equation~\\eqref{{eq:tsgg-trust}} summarises macro families for
reporting; trust propagation supplies a \\emph{{vertex-level theory}} with auditable
$T(v)$ and $T(\\pi)$ for institutional review.

\\paragraph{{Disclaimer.}}
{report.disclaimer}
"""
    path.write_text(content, encoding="utf-8")


def write_trust_flow_figure_include(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = """\\begin{figure}[htbp]
  \\centering
  \\includegraphics[width=\\linewidth]{figures/trust_flow_graph.pdf}
  \\caption{Trust propagation over TSGG: $T(v)\\in[0,1]$ at each stage with operators
    $\\rho,\\sigma,\\kappa,\\omega,\\delta,\\alpha$. Edge labels show compositional decay.}
  \\label{fig:trust-flow-graph}
\\end{figure}
"""
    path.write_text(content, encoding="utf-8")


def write_trust_propagation_metrics_table(report: TrustPropagationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    m = report.metrics
    lines = [
        "% Auto-generated by dualexis trust propagation export",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Trust propagation metrics on TSGG.}",
        "  \\label{tab:trust-propagation-metrics}",
        "  \\small",
        "  \\begin{tabular}{@{}lr@{}}",
        "    \\toprule",
        "    Metric & Value \\\\",
        "    \\midrule",
        f"    Benchmark prior $\\pi_0$ & {report.benchmark_trust_prior:.3f} \\\\",
        f"    Mean node trust $\\bar{{T}}_V$ & {m.mean_node_trust:.3f} \\\\",
        f"    Mean path trust $\\bar{{T}}_\\pi$ & {m.mean_path_trust:.3f} \\\\",
        f"    Mean recommendation trust $\\bar{{T}}_r$ & {m.mean_recommendation_trust:.3f} \\\\",
        f"    trust\\_consistency & {m.trust_consistency:.3f} \\\\",
        f"    trust\\_decay & {m.trust_decay:.3f} \\\\",
        f"    trust\\_recovery & {m.trust_recovery:.3f} \\\\",
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_trust_flow_graph_pdf(path: Path, report: TrustPropagationReport) -> None:
    """Compile TikZ trust-flow figure with stage mean trust."""
    path.parent.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]
    tex_source = repo_root / "paper" / "figures" / "trust_flow_graph.tex"
    if not tex_source.is_file():
        _write_trust_flow_tikz_source(tex_source, report)

    by_kind: dict[TrustNodeKind, list[float]] = {kind: [] for kind in STAGE_ORDER}
    for node in report.nodes:
        by_kind[node.kind].append(node.trust)
    stage_labels = ["Evidence", "Safety", "Causal", "Recom.", "Govern.", "Audit"]
    stage_means = [
        statistics.mean(by_kind[kind]) if by_kind[kind] else 0.0 for kind in STAGE_ORDER
    ]
    build_copy = path.parent / "trust_flow_graph_build.tex"
    build_copy.write_text(
        _tikz_body(stage_labels, stage_means, report.benchmark_trust_prior),
        encoding="utf-8",
    )
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        if not path.exists():
            path.write_bytes(b"% PDF placeholder\n")
        return
    subprocess.run(
        [pdflatex, "-interaction=nonstopmode", "-halt-on-error", build_copy.name],
        cwd=path.parent,
        check=False,
        capture_output=True,
    )
    built = path.parent / "trust_flow_graph_build.pdf"
    if built.is_file():
        shutil.copy(built, path)


def _write_trust_flow_tikz_source(path: Path, report: TrustPropagationReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_kind: dict[TrustNodeKind, list[float]] = {kind: [] for kind in STAGE_ORDER}
    for node in report.nodes:
        by_kind[node.kind].append(node.trust)
    stage_means = [
        statistics.mean(by_kind[kind]) if by_kind[kind] else 0.0 for kind in STAGE_ORDER
    ]
    path.write_text(
        _tikz_body(
            ["Evidence", "Safety", "Causal", "Recom.", "Govern.", "Audit"],
            stage_means,
            report.benchmark_trust_prior,
        ),
        encoding="utf-8",
    )


def _tikz_body(labels: list[str], means: list[float], prior: float) -> str:
    node_names = [f"n{index}" for index in range(len(labels))]
    nodes_tex = []
    for index, (label, mean) in enumerate(zip(labels, means, strict=True)):
        x_pos = index * 2.2
        nodes_tex.append(
            f"\\node[stage] ({node_names[index]}) at ({x_pos},0) {{{label}\\\\$T={mean:.2f}$}};"
        )
    arrows = []
    for index in range(len(labels) - 1):
        decay = means[index] - means[index + 1] if means[index] > 0 else 0.0
        arrows.append(
            f"\\draw[flow] ({node_names[index]}) -- ({node_names[index + 1]}) "
            f"node[midway,above,font=\\scriptsize] {{$\\downarrow{decay:.2f}$}};"
        )
    return f"""\\documentclass[border=2pt]{{standalone}}
\\usepackage{{tikz}}
\\usetikzlibrary{{arrows.meta,positioning}}
\\begin{{document}}
\\begin{{tikzpicture}}[
  stage/.style={{draw, rounded corners=3pt, minimum width=1.7cm, minimum height=0.9cm,
                align=center, font=\\footnotesize\\bfseries, fill=blue!12}},
  flow/.style={{-{{Stealth[length=2mm]}}, thick, draw=blue!55!black}},
]
\\node[font=\\scriptsize] at (5.5,1.1) {{$\\pi_0={prior:.2f}$}};
{chr(10).join(nodes_tex)}
{chr(10).join(arrows)}
\\node[font=\\small\\bfseries] at (5.5,-1.2) {{Trust-aware TSGG propagation}};
\\end{{tikzpicture}}
\\end{{document}}
"""


def export_trust_propagation_artifacts(
    report: TrustPropagationReport,
    output_dir: Path,
    *,
    paper_sections: Path | None = None,
    paper_tables: Path | None = None,
    paper_figures: Path | None = None,
) -> dict[str, str]:
    """Write JSON, CSV, and paper artefacts for trust propagation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / "trust_propagation_report.json"
    payload = report.model_dump(mode="json")
    payload["generated_at"] = report.generated_at.isoformat()
    report_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    sections = paper_sections or Path("results_reference/sections")
    tables = paper_tables or Path("results_reference/tables")
    figures = paper_figures or Path("results_reference/figures")

    section_tex = sections / "trust_propagation.tex"
    figure_include = sections / "trust_flow_figure.tex"
    table_tex = tables / "trust_propagation_metrics.tex"
    figure_pdf = figures / "trust_flow_graph.pdf"

    write_trust_propagation_section(report, section_tex)
    write_trust_flow_figure_include(figure_include)
    write_trust_propagation_metrics_table(report, table_tex)
    generate_trust_flow_graph_pdf(figure_pdf, report)

    return {
        "report_json": str(report_json),
        "section_tex": str(section_tex),
        "table_tex": str(table_tex),
        "figure_pdf": str(figure_pdf),
    }


__all__ = [
    "TrustNode",
    "TrustNodeKind",
    "TrustPath",
    "TrustPropagationMetrics",
    "TrustPropagationReport",
    "aggregate_trust_metrics",
    "audit_confidence",
    "benchmark_trust_prior",
    "causal_confidence",
    "compose_trust",
    "evidence_reliability",
    "export_trust_propagation_artifacts",
    "generate_trust_flow_graph_pdf",
    "governance_confidence",
    "propagate_trust_batch",
    "propagate_trust_for_record",
    "recommendation_confidence",
    "safety_state_confidence",
    "write_trust_propagation_section",
]
