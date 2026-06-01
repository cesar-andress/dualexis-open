"""Privacy fuzz battery with exportable results (synthetic validation only)."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dualexis.core.exceptions import PrivacyViolationError
from dualexis.privacy_runtime import DEFAULT_PRIVACY_POLICY, strip_raw_media, validate_payload_privacy
from dualexis.privacy_runtime.models import PrivacyViolationType, classify_forbidden_field
from dualexis.schemas.perception import Modality, PerceptionFrame
from dualexis.privacy_runtime.service import DefaultPrivacyRuntimeService

PRIVACY_FUZZ_DISCLAIMER = (
    "Privacy fuzz battery on representative payloads. "
    "Reports pass/fail for fail-closed validation only; not a certification audit."
)


@dataclass(frozen=True)
class PrivacyFuzzCase:
    """One fuzz probe against L1 validators."""

    case_id: str
    category: str
    description: str
    payload: dict[str, object]
    expect_rejection: bool
    nested: bool = False


@dataclass(frozen=True)
class PrivacyFuzzResult:
    """Outcome of a single fuzz case."""

    case_id: str
    category: str
    description: str
    expect_rejection: bool
    rejected: bool
    violation_type: str
    strip_removed_media: bool


def default_fuzz_cases() -> tuple[PrivacyFuzzCase, ...]:
    """Representative probes requested for validation harness defensibility."""
    return (
        PrivacyFuzzCase(
            "identity_student_id",
            "identity",
            "Forbidden identity field student_id",
            {"zone_id": "z1", "student_id": "S-001"},
            True,
        ),
        PrivacyFuzzCase(
            "identity_person_name",
            "identity",
            "Forbidden identity field name",
            {"zone_id": "z1", "name": "Ada"},
            True,
        ),
        PrivacyFuzzCase(
            "biometric_face_embedding",
            "biometric",
            "Forbidden face_embedding field",
            {"zone_id": "z1", "face_embedding": [0.1, 0.2]},
            True,
        ),
        PrivacyFuzzCase(
            "biometric_facial_embedding",
            "biometric",
            "Forbidden facial_embedding alias",
            {"zone_id": "z1", "facial_embedding": "vector"},
            True,
        ),
        PrivacyFuzzCase(
            "raw_media_paths",
            "media",
            "Raw video/audio paths in payload",
            {
                "zone_id": "z1",
                "raw_video_path": "/tmp/v.mp4",
                "raw_audio_path": "/tmp/a.wav",
            },
            True,
        ),
        PrivacyFuzzCase(
            "nested_metadata_identity",
            "nested",
            "Nested metadata injection with person_id",
            {"zone_id": "z1", "metadata": {"nested": {"person_id": "p-9"}}},
            True,
            nested=True,
        ),
        PrivacyFuzzCase(
            "obfuscated_student_substring_key",
            "obfuscation",
            "Key containing forbidden substring student",
            {"zone_id": "z1", "campus_student_ref": "hidden"},
            True,
        ),
        PrivacyFuzzCase(
            "obfuscated_face_key",
            "obfuscation",
            "Key containing forbidden substring face",
            {"zone_id": "z1", "zone_face_probe": "opaque"},
            True,
        ),
        PrivacyFuzzCase(
            "control_zone_only",
            "control",
            "Benign zone-level payload",
            {"zone_id": "cafeteria", "density": "0.42"},
            False,
        ),
    )


def run_privacy_fuzz_case(case: PrivacyFuzzCase) -> PrivacyFuzzResult:
    """Execute one fuzz case against validate_payload_privacy."""
    rejected = False
    violation_type = ""
    try:
        validate_payload_privacy(case.payload, DEFAULT_PRIVACY_POLICY)
    except PrivacyViolationError as exc:
        rejected = True
        violation_type = str(exc)

    stripped = strip_raw_media(case.payload)
    strip_removed = any(
        key in case.payload and key not in stripped
        for key in ("raw_video_path", "raw_audio_path", "frame_data", "raw_video", "raw_audio")
    )

    if case.category == "media" and not rejected:
        for key in case.payload:
            if classify_forbidden_field(str(key)).value == PrivacyViolationType.MEDIA.value:
                rejected = True
                violation_type = "media_field_detected"

    return PrivacyFuzzResult(
        case_id=case.case_id,
        category=case.category,
        description=case.description,
        expect_rejection=case.expect_rejection,
        rejected=rejected,
        violation_type=violation_type,
        strip_removed_media=strip_removed,
    )


def run_frame_media_fuzz() -> PrivacyFuzzResult:
    """Persistent payload_ref on perception frame (TB1)."""
    runtime = DefaultPrivacyRuntimeService()
    frame = PerceptionFrame(
        modality=Modality.VIDEO,
        node_id="fuzz",
        zone_id="hall-a",
        payload_ref="/data/forbidden_clip.mp4",
    )
    rejected = False
    violation_type = ""
    try:
        runtime.validate_frame(frame)
    except PrivacyViolationError as exc:
        rejected = True
        violation_type = str(exc)
    return PrivacyFuzzResult(
        case_id="frame_persistent_media",
        category="media",
        description="Persistent payload_ref on PerceptionFrame",
        expect_rejection=True,
        rejected=rejected,
        violation_type=violation_type,
        strip_removed_media=False,
    )


def run_privacy_fuzz_battery(
    cases: Sequence[PrivacyFuzzCase] | None = None,
) -> tuple[PrivacyFuzzResult, ...]:
    """Run all fuzz cases plus frame-level probe."""
    selected = list(cases or default_fuzz_cases())
    results = [run_privacy_fuzz_case(case) for case in selected]
    results.append(run_frame_media_fuzz())
    return tuple(results)


def export_privacy_fuzz_results(
    output_dir: str | Path,
    *,
    results: Sequence[PrivacyFuzzResult] | None = None,
    latex_path: str | Path | None = None,
) -> Path:
    """Write CSV and optional LaTeX table."""
    out_root = Path(output_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    rows = list(results or run_privacy_fuzz_battery())

    csv_path = out_root / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "category",
                "description",
                "expect_rejection",
                "rejected",
                "pass",
                "violation_type",
                "strip_removed_media",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "case_id": row.case_id,
                    "category": row.category,
                    "description": row.description,
                    "expect_rejection": row.expect_rejection,
                    "rejected": row.rejected,
                    "pass": row.rejected == row.expect_rejection,
                    "violation_type": row.violation_type,
                    "strip_removed_media": row.strip_removed_media,
                }
            )

    tex_target = Path(latex_path) if latex_path else out_root / "privacy_fuzz_results.tex"
    tex_target.parent.mkdir(parents=True, exist_ok=True)
    tex_target.write_text(generate_privacy_fuzz_latex(rows), encoding="utf-8")
    return csv_path


def generate_privacy_fuzz_latex(results: Sequence[PrivacyFuzzResult]) -> str:
    """Build LaTeX table for the manuscript."""
    lines = [
        "% Auto-generated by dualexis evaluation privacy_fuzz_battery.",
        "% Fuzz probes only — not a certification audit.",
        "",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Privacy-runtime fuzz probes (fail-closed validation on representative payloads). "
        "Pass indicates observed behaviour matches expectation; synthetic test harness only.}",
        "  \\label{tab:privacy-fuzz}",
        "  \\small",
        "  \\begin{tabular}{@{}llcc@{}}",
        "    \\toprule",
        "    Case & Category & Expected reject & Observed \\\\",
        "    \\midrule",
    ]
    for row in results:
        expected = "Yes" if row.expect_rejection else "No"
        observed = "Reject" if row.rejected else "Allow"
        pass_mark = "$\\checkmark$" if row.rejected == row.expect_rejection else "$\\times$"
        case_tex = row.case_id.replace("_", r"\_")
        lines.append(
            f"    {case_tex} & {row.category} & {expected} & {observed} {pass_mark} \\\\"
        )
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def run_extended_privacy_stress():
    """
    Run forbidden-key fuzz plus adversarial privacy stress (linkage attacks).

    Returns :class:`AdversarialPrivacyReport` from ``dualexis.adversarial_privacy``.
    """
    from dualexis.adversarial_privacy.stress import run_adversarial_privacy_stress

    return run_adversarial_privacy_stress()


__all__ = [
    "PRIVACY_FUZZ_DISCLAIMER",
    "PrivacyFuzzCase",
    "PrivacyFuzzResult",
    "default_fuzz_cases",
    "export_privacy_fuzz_results",
    "generate_privacy_fuzz_latex",
    "run_extended_privacy_stress",
    "run_privacy_fuzz_battery",
]
