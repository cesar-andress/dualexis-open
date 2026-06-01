"""Export adversarial privacy stress artefacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dualexis.adversarial_privacy.models import AdversarialPrivacyReport
from dualexis.evaluation.privacy_fuzz_battery import export_privacy_fuzz_results


def export_adversarial_privacy_stress(
    report: AdversarialPrivacyReport,
    output_dir: Path,
    *,
    paper_sections: Path | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    fuzz_dir = output_dir / "fuzz_baseline"
    fuzz_csv = export_privacy_fuzz_results(fuzz_dir)

    attack_rows: list[dict[str, str | float | bool]] = []
    for result in report.adversarial_results:
        attack_rows.append(
            {
                "attack_id": result.attack_id,
                "kind": result.kind.value,
                "l1_blocked": result.l1_blocked,
                "attack_succeeded": result.attack_succeeded,
                "reidentification_risk": result.reidentification_risk,
                "semantic_leakage_score": result.semantic_leakage_score,
                "violation_type": result.violation_type[:200],
            }
        )

    attacks_csv = output_dir / "adversarial_attacks.csv"
    with attacks_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(attack_rows[0].keys()))
        writer.writeheader()
        writer.writerows(attack_rows)

    metrics_csv = output_dir / "adversarial_metrics.csv"
    metrics = report.metrics
    with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "reidentification_risk",
                "privacy_attack_success_rate",
                "semantic_leakage_score",
                "privacy_resilience_index",
                "fuzz_pass_rate",
                "l1_block_rate",
                "attack_count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "reidentification_risk": metrics.reidentification_risk,
                "privacy_attack_success_rate": metrics.privacy_attack_success_rate,
                "semantic_leakage_score": metrics.semantic_leakage_score,
                "privacy_resilience_index": metrics.privacy_resilience_index,
                "fuzz_pass_rate": metrics.fuzz_pass_rate,
                "l1_block_rate": metrics.l1_block_rate,
                "attack_count": metrics.attack_count,
            }
        )

    summary_path = output_dir / "adversarial_privacy_report.json"
    summary_path.write_text(
        json.dumps(
            {
                "disclaimer": report.disclaimer,
                "generated_at": report.generated_at.isoformat(),
                "metrics": metrics.model_dump(),
                "fuzz_case_count": report.fuzz_case_count,
                "fuzz_pass_count": report.fuzz_pass_count,
                "attacks": [r.model_dump() for r in report.adversarial_results],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    paths = {
        "fuzz_csv": str(fuzz_csv),
        "attacks_csv": str(attacks_csv),
        "metrics_csv": str(metrics_csv),
        "report_json": str(summary_path),
    }

    if paper_sections is not None:
        section_path = paper_sections / "adversarial_privacy.tex"
        write_adversarial_privacy_section(report, section_path)
        paths["section_tex"] = str(section_path)

    return paths


def write_adversarial_privacy_section(
    report: AdversarialPrivacyReport,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    m = report.metrics
    attack_lines = []
    for result in report.adversarial_results:
        kind_tex = result.kind.value.replace("_", r"\_")
        blocked = "blocked" if result.l1_blocked else "residual risk"
        attack_lines.append(
            f"  \\item \\textbf{{{kind_tex}}} --- {blocked}; "
            f"$r_{{\\mathrm{{reid}}}}$={result.reidentification_risk:.2f}, "
            f"semantic leakage={result.semantic_leakage_score:.2f}."
        )

    content = f"""\\subsection{{Adversarial Privacy Stress Framework}}
\\label{{sec:adversarial-privacy}}

The privacy fuzz battery (Section~\\ref{{sec:privacy-fuzz-methodology}}) attests
\\textbf{{fail-closed forbidden-key validation}}. We extend it into an \\textbf{{adversarial
privacy stress framework}} that evaluates privacy \\emph{{beyond}} literal deny lists:
linkage, quasi-identifiers, and semantic residual risk under stochastic world dynamics.

\\paragraph{{Threat classes.}}
\\begin{{itemize}}[noitemsep]
{chr(10).join(attack_lines)}
\\end{{itemize}}

\\paragraph{{Metrics.}}
\\begin{{itemize}}[noitemsep]
  \\item \\textbf{{reidentification\\_risk}} --- estimated uniqueness from quasi-identifiers
        and indirect identity hints ($\\bar{{r}}={m.reidentification_risk:.3f}$).
  \\item \\textbf{{privacy\\_attack\\_success\\_rate}} --- fraction of attacks that publish
        linkable semantics without L1 block ({m.privacy_attack_success_rate:.3f}).
  \\item \\textbf{{semantic\\_leakage\\_score}} --- residual linkable attributes if payloads
        passed the validator ($\\bar{{s}}={m.semantic_leakage_score:.3f}$).
  \\item \\textbf{{privacy\\_resilience\\_index}} --- composite resilience score
        $R_{{\\mathrm{{priv}}}}={m.privacy_resilience_index:.3f}$ combining low attack success,
        low re-identification risk, fuzz pass rate ({m.fuzz_pass_rate:.3f}), and L1 block rate
        ({m.l1_block_rate:.3f}).
\\end{{itemize}}

\\paragraph{{Interpretation.}}
A high fuzz pass rate with non-zero adversarial success rate indicates that
\\emph{{schema-level deny lists are necessary but insufficient}}: institutional review must
also govern quasi-identifiers, temporal linkage, and graph-structured metadata on the
semantic event path. Artefacts export to \\texttt{{results/adversarial\\_privacy/}}.

\\paragraph{{Relation to forbidden-key fuzz.}}
The legacy fuzz suite ({report.fuzz_pass_count}/{report.fuzz_case_count} probes passed) remains
the first line of defense; adversarial stress quantifies the \\textbf{{residual attack surface}}
for expert-system deployments.
"""
    path.write_text(content, encoding="utf-8")


__all__ = ["export_adversarial_privacy_stress", "write_adversarial_privacy_section"]
