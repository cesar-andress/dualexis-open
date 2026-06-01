"""End-to-end TSGG pipeline orchestration."""

from __future__ import annotations

from dualexis.cssg.runner import build_cssg_trace_from_scenario
from dualexis.governance.cases import collect_pipeline_cases
from dualexis.governance.formal_models import GovernanceDecisionTrace
from dualexis.governance.state_machine import build_decision_trace
from dualexis.governance.simulator import simulate_operator_decision
from dualexis.governance.models import OperatorProfile
from dualexis.pipeline import run_pipeline
from dualexis.pipeline.config import PipelineRunConfig
from dualexis.tsgg.models import TsggRunRecord

TSGG_PIPELINE_CONFIG = PipelineRunConfig(
    enable_privacy_runtime=True,
    enable_temporal_graph=True,
    enable_explanation_layer=True,
    enable_sssg=True,
)


def run_tsgg_record(
    scenario_id: str,
    *,
    seed: int = 1,
    governance_profile: OperatorProfile = OperatorProfile.BALANCED,
    governance_seed: int = 17,
) -> TsggRunRecord:
    """
    Execute the TSGG chain for one (scenario, seed):

    evidence → safety state → causal transition → recommendation →
    governance decision → audit trace.
    """
    import random

    causal_trace = build_cssg_trace_from_scenario(scenario_id, seed=seed)
    pipeline_output = run_pipeline(
        scenario_id,
        seed=seed,
        run_config=TSGG_PIPELINE_CONFIG,
    )

    cases = collect_pipeline_cases(scenarios=(scenario_id,), seeds=(seed,))
    gov_traces: list[GovernanceDecisionTrace] = []
    profile_rng = random.Random(governance_seed + seed)

    for case in cases:
        decision = simulate_operator_decision(case, profile=governance_profile, rng=profile_rng)
        gov_traces.append(build_decision_trace(case, decision))

    evidence_count = sum(len(t.supporting_evidence) for t in causal_trace.causal_transitions)
    return TsggRunRecord(
        scenario_id=scenario_id,
        seed=seed,
        causal_trace=causal_trace,
        pipeline_output=pipeline_output,
        governance_traces=tuple(gov_traces),
        stage_counts={
            "evidence": evidence_count,
            "safety_state": len(causal_trace.snapshots),
            "causal_transition": len(causal_trace.causal_transitions),
            "recommendation": len(pipeline_output.recommendations),
            "governance_decision": len(gov_traces),
            "audit_trace": sum(len(t.steps) for t in gov_traces),
        },
    )


__all__ = ["TSGG_PIPELINE_CONFIG", "run_tsgg_record"]
