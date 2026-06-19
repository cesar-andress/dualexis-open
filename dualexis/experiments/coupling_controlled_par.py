"""Coupling-controlled PAR decomposition diagnostic experiment."""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.evaluation.procedural_agreement import (
    BootstrapInterval,
    aggregate_micro_rates,
    bootstrap_ci,
    chance_par_baseline,
    procedural_agreement_metrics,
)
from dualexis.experiments.empirical_battery import DEFAULT_SEEDS, PAPER_SCENARIOS
from dualexis.simulation.coupling_perturbation import (
    DEFAULT_LAMBDAS,
    CouplingChannel,
    CouplingPerturbationConfig,
    apply_coupling_perturbation,
    retained_coupling_proxy,
)
from dualexis.simulation.emission_mode import EmissionMode
from dualexis.simulation.event_generator import SyntheticEventGenerator
from dualexis.simulation.ground_truth import ScenarioGroundTruth
from dualexis.simulation.independent_labeler import build_independent_ground_truth
from dualexis.simulation.scenario import get_scenario_definition, resolve_scenario
from dualexis.simulation.world import WorldState, build_default_world, initial_world_state
from dualexis.simulation.world_dynamics import advance_world_state
from dualexis.semantic_events.models import EventSource, SemanticEvent

COUPLING_PAR_DISCLAIMER = (
    "Coupling-controlled PAR decomposition: diagnostic experiment only. Perturbations corrupt "
    "emitter-visible simulator variables while the ground-truth oracle remains on clean state. "
    "Not operational safety, deployment validity, or a new headline superiority claim."
)

def _simulator_events(events: tuple[SemanticEvent, ...]) -> tuple[SemanticEvent, ...]:
    return tuple(event for event in events if event.source == EventSource.SIMULATOR)


def _chance_baseline_seed(seed: int, lam: float, channel: CouplingChannel) -> int:
    import hashlib

    digest = hashlib.sha256(f"{seed}:{lam}:{channel.value}".encode()).hexdigest()
    return int(digest[:8], 16)


DEFAULT_CHANNELS: tuple[CouplingChannel, ...] = (
    CouplingChannel.ZONE_PERMUTATION,
    CouplingChannel.TEMPORAL_DESYNC,
    CouplingChannel.NOISE_INJECTION,
)


@dataclass(frozen=True)
class CouplingRunResult:
    scenario: str
    seed: int
    channel: str
    lambda_: float
    par: float
    fpr: float
    fnr: float
    par_zero: float
    delta_proc: float
    coupling_proxy: float


@dataclass(frozen=True)
class CouplingAggregateRow:
    channel: str
    lambda_: float
    coupling_proxy: float
    par: float
    fpr: float
    fnr: float
    par_ci: BootstrapInterval
    par_zero: float
    par_zero_ci: BootstrapInterval
    delta_proc: float
    delta_proc_ci: BootstrapInterval
    par_decay_slope: float | None


@dataclass(frozen=True)
class CouplingControlledParReport:
    generated_at: datetime
    scenarios: tuple[str, ...]
    seeds: tuple[int, ...]
    lambdas: tuple[float, ...]
    channels: tuple[str, ...]
    chance_permutations: int
    aggregate_rows: tuple[CouplingAggregateRow, ...]
    disclaimer: str


def run_coupling_controlled_scenario(
    name: str,
    *,
    seed: int,
    config: CouplingPerturbationConfig,
) -> tuple[tuple[SemanticEvent, ...], ScenarioGroundTruth, float]:
    """Simulate with perturbed emitter view; GT built from clean dynamics."""
    scenario_id = resolve_scenario(name)
    definition = get_scenario_definition(scenario_id)
    rng = random.Random(seed)
    graph = build_default_world()
    state = initial_world_state(graph)
    generator = SyntheticEventGenerator(
        emission_mode=EmissionMode.DECOUPLED,
        seed=seed,
    )
    history: list[WorldState] = []
    coupling_values: list[float] = []
    events: list[SemanticEvent] = []

    for _step in range(definition.duration_steps):
        state = advance_world_state(state, graph, definition, scenario_id, rng)
        history.append(state)
        perturbed = apply_coupling_perturbation(
            state,
            config=config,
            history=tuple(history),
        )
        coupling_values.append(retained_coupling_proxy(state, perturbed))
        tick_events = generator.generate_events(
            perturbed,
            scenario_id=scenario_id,
            tick_seconds=definition.tick_seconds,
        )
        events.extend(tick_events)

    ground_truth = build_independent_ground_truth(scenario_id, seed=seed)
    mean_coupling = round(sum(coupling_values) / len(coupling_values), 4) if coupling_values else 1.0
    return tuple(events), ground_truth, mean_coupling


def _linear_slope(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0.0:
        return None
    return round(num / den, 4)


def run_coupling_controlled_par_experiment(
    *,
    output_dir: Path,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    lambdas: tuple[float, ...] = DEFAULT_LAMBDAS,
    channels: tuple[CouplingChannel, ...] = DEFAULT_CHANNELS,
    chance_permutations: int = 1000,
) -> CouplingControlledParReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_rows: list[CouplingRunResult] = []
    aggregate_rows: list[CouplingAggregateRow] = []

    for channel in channels:
        channel_par_by_lambda: list[tuple[float, float]] = []
        channel_row_indices: list[int] = []
        for lam in lambdas:
            per_run_metrics = []
            per_run_par_zero: list[float] = []
            per_run_delta: list[float] = []
            per_run_coupling: list[float] = []
            for scenario in scenarios:
                for seed in seeds:
                    config = CouplingPerturbationConfig(
                        channel=channel,
                        lambda_=lam,
                        seed=seed,
                    )
                    raw_events, ground_truth, coupling_proxy = run_coupling_controlled_scenario(
                        scenario,
                        seed=seed,
                        config=config,
                    )
                    sim_events = _simulator_events(raw_events)
                    metrics = procedural_agreement_metrics(sim_events, ground_truth)
                    par_zero, _ = chance_par_baseline(
                        sim_events,
                        ground_truth,
                        n_permutations=chance_permutations,
                        seed=_chance_baseline_seed(seed, lam, channel),
                    )
                    delta = round(metrics.par - par_zero, 4)
                    per_run_metrics.append(metrics)
                    per_run_par_zero.append(par_zero)
                    per_run_delta.append(delta)
                    per_run_coupling.append(coupling_proxy)
                    run_rows.append(
                        CouplingRunResult(
                            scenario=scenario,
                            seed=seed,
                            channel=channel.value,
                            lambda_=lam,
                            par=metrics.par,
                            fpr=metrics.fpr,
                            fnr=metrics.fnr,
                            par_zero=par_zero,
                            delta_proc=delta,
                            coupling_proxy=coupling_proxy,
                        )
                    )

            agg = aggregate_micro_rates(per_run_metrics)
            par_values = [m.par for m in per_run_metrics]
            channel_par_by_lambda.append((lam, agg.par))
            channel_row_indices.append(len(aggregate_rows))
            aggregate_rows.append(
                CouplingAggregateRow(
                    channel=channel.value,
                    lambda_=lam,
                    coupling_proxy=round(sum(per_run_coupling) / len(per_run_coupling), 4),
                    par=agg.par,
                    fpr=agg.fpr,
                    fnr=agg.fnr,
                    par_ci=bootstrap_ci(par_values),
                    par_zero=round(sum(per_run_par_zero) / len(per_run_par_zero), 4),
                    par_zero_ci=bootstrap_ci(per_run_par_zero),
                    delta_proc=round(sum(per_run_delta) / len(per_run_delta), 4),
                    delta_proc_ci=bootstrap_ci(per_run_delta),
                    par_decay_slope=None,
                )
            )

        slope = _linear_slope(
            [item[0] for item in channel_par_by_lambda],
            [item[1] for item in channel_par_by_lambda],
        )
        if slope is not None:
            for idx in channel_row_indices:
                row = aggregate_rows[idx]
                if row.lambda_ == 1.0:
                    aggregate_rows[idx] = CouplingAggregateRow(
                        channel=row.channel,
                        lambda_=row.lambda_,
                        coupling_proxy=row.coupling_proxy,
                        par=row.par,
                        fpr=row.fpr,
                        fnr=row.fnr,
                        par_ci=row.par_ci,
                        par_zero=row.par_zero,
                        par_zero_ci=row.par_zero_ci,
                        delta_proc=row.delta_proc,
                        delta_proc_ci=row.delta_proc_ci,
                        par_decay_slope=slope,
                    )

    report = CouplingControlledParReport(
        generated_at=datetime.now(tz=UTC),
        scenarios=scenarios,
        seeds=seeds,
        lambdas=lambdas,
        channels=tuple(channel.value for channel in channels),
        chance_permutations=chance_permutations,
        aggregate_rows=tuple(aggregate_rows),
        disclaimer=COUPLING_PAR_DISCLAIMER,
    )

    _write_run_csv(output_dir / "coupling_controlled_par_by_run.csv", run_rows)
    _write_aggregate_csv(output_dir / "coupling_controlled_par.csv", aggregate_rows)
    _write_json(output_dir / "coupling_controlled_par.json", report, run_rows)
    _write_latex(output_dir / "coupling_controlled_par.tex", aggregate_rows)
    return report


def _write_run_csv(path: Path, rows: list[CouplingRunResult]) -> None:
    fieldnames = [
        "scenario",
        "seed",
        "channel",
        "lambda",
        "par",
        "fpr",
        "fnr",
        "par_zero",
        "delta_proc",
        "coupling_proxy",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "scenario": row.scenario,
                    "seed": row.seed,
                    "channel": row.channel,
                    "lambda": row.lambda_,
                    "par": row.par,
                    "fpr": row.fpr,
                    "fnr": row.fnr,
                    "par_zero": row.par_zero,
                    "delta_proc": row.delta_proc,
                    "coupling_proxy": row.coupling_proxy,
                }
            )


def _write_aggregate_csv(path: Path, rows: list[CouplingAggregateRow]) -> None:
    fieldnames = [
        "channel",
        "lambda",
        "coupling_proxy",
        "par",
        "fpr",
        "fnr",
        "par_ci_lower",
        "par_ci_upper",
        "par_zero",
        "par_zero_ci_lower",
        "par_zero_ci_upper",
        "delta_proc",
        "delta_proc_ci_lower",
        "delta_proc_ci_upper",
        "par_decay_slope",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "channel": row.channel,
                    "lambda": row.lambda_,
                    "coupling_proxy": row.coupling_proxy,
                    "par": row.par,
                    "fpr": row.fpr,
                    "fnr": row.fnr,
                    "par_ci_lower": row.par_ci.lower,
                    "par_ci_upper": row.par_ci.upper,
                    "par_zero": row.par_zero,
                    "par_zero_ci_lower": row.par_zero_ci.lower,
                    "par_zero_ci_upper": row.par_zero_ci.upper,
                    "delta_proc": row.delta_proc,
                    "delta_proc_ci_lower": row.delta_proc_ci.lower,
                    "delta_proc_ci_upper": row.delta_proc_ci.upper,
                    "par_decay_slope": row.par_decay_slope,
                }
            )


def _write_json(
    path: Path,
    report: CouplingControlledParReport,
    run_rows: list[CouplingRunResult],
) -> None:
    payload = {
        "generated_at": report.generated_at.isoformat(),
        "scenarios": list(report.scenarios),
        "seeds": list(report.seeds),
        "lambdas": list(report.lambdas),
        "channels": list(report.channels),
        "chance_permutations": report.chance_permutations,
        "disclaimer": report.disclaimer,
        "aggregate": [
            {
                "channel": row.channel,
                "lambda": row.lambda_,
                "coupling_proxy": row.coupling_proxy,
                "par": row.par,
                "fpr": row.fpr,
                "fnr": row.fnr,
                "par_ci_95": [row.par_ci.lower, row.par_ci.upper],
                "par_zero": row.par_zero,
                "par_zero_ci_95": [row.par_zero_ci.lower, row.par_zero_ci.upper],
                "delta_proc": row.delta_proc,
                "delta_proc_ci_95": [row.delta_proc_ci.lower, row.delta_proc_ci.upper],
                "par_decay_slope": row.par_decay_slope,
            }
            for row in report.aggregate_rows
        ],
        "run_count": len(run_rows),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_latex(path: Path, rows: list[CouplingAggregateRow]) -> None:
    lines = [
        "% Auto-generated by dualexis coupling_controlled_par experiment.",
        "% Diagnostic coupling-controlled PAR decomposition; not primary conformance evidence.",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Coupling-controlled PAR decomposition. Emitter-visible simulator variables are "
        "perturbed while the GT oracle remains on clean state. $\\Delta_{\\mathrm{proc}} = "
        "PAR - PAR_0$ where $PAR_0$ is a label-permutation chance baseline ($N{=}1000$). "
        "Diagnostic only; not operational safety or deployment validity.}",
        "  \\label{tab:coupling-controlled-par}",
        "  \\scriptsize",
        "  \\setlength{\\tabcolsep}{3pt}",
        "  \\begin{tabular}{@{}llrrrrrrl@{}}",
        "    \\toprule",
        "    Channel & $\\lambda$ & Coupling & PAR & FPR & FNR & $PAR_0$ & "
        "$\\Delta_{\\mathrm{proc}}$ & 95\\% CI $\\Delta$ \\\\",
        "    \\midrule",
    ]
    channel_labels = {
        "zone_permutation": "Zone perm.",
        "temporal_desync": "Temporal lag",
        "noise_injection": "Noise",
    }
    for row in rows:
        channel_tex = channel_labels.get(row.channel, row.channel.replace("_", r"\_"))
        delta_ci = f"[{row.delta_proc_ci.lower:.3f}, {row.delta_proc_ci.upper:.3f}]"
        lines.append(
            f"    {channel_tex} & {row.lambda_:.2f} & {row.coupling_proxy:.3f} & "
            f"{row.par:.3f} & {row.fpr:.3f} & {row.fnr:.3f} & {row.par_zero:.3f} & "
            f"{row.delta_proc:.3f} & {delta_ci} \\\\"
        )
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


__all__ = [
    "COUPLING_PAR_DISCLAIMER",
    "CouplingAggregateRow",
    "CouplingControlledParReport",
    "CouplingRunResult",
    "DEFAULT_CHANNELS",
    "run_coupling_controlled_par_experiment",
    "run_coupling_controlled_scenario",
]
