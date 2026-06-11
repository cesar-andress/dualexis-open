"""Derive harness honesty Pass/Partial/Fail labels from B5 baseline CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from dualexis.experiments.empirical_battery import PAPER_SCENARIOS

SUGGESTED_COMMAND = (
    "python3.12 -m dualexis.cli experiment validate-tsgg"
)

PASS_THRESHOLD = 1.0
FAIL_THRESHOLD = 0.0
MEAN_TOLERANCE = 1e-9


class HarnessB5InputError(FileNotFoundError):
    """Missing baseline CSV or required B5 rows for Table 8."""


@dataclass(frozen=True)
class HarnessB5ScenarioRow:
    scenario: str
    mean_detection_accuracy: float
    seed_count: int
    label: str


@dataclass(frozen=True)
class HarnessB5Alignment:
    paper_baseline: str
    rows: tuple[HarnessB5ScenarioRow, ...]

    @property
    def seed_count(self) -> int:
        counts = {row.seed_count for row in self.rows}
        if len(counts) != 1:
            raise HarnessB5InputError(
                f"Inconsistent seed counts across scenarios: {sorted(counts)}"
            )
        return counts.pop()


def classify_detection_accuracy(mean_accuracy: float) -> str:
    """Map mean B5 event_detection_accuracy to Pass/Partial/Fail."""
    if abs(mean_accuracy - PASS_THRESHOLD) <= MEAN_TOLERANCE:
        return "Pass"
    if abs(mean_accuracy - FAIL_THRESHOLD) <= MEAN_TOLERANCE:
        return "Fail"
    if FAIL_THRESHOLD < mean_accuracy < PASS_THRESHOLD:
        return "Partial"
    raise HarnessB5InputError(
        f"Mean detection accuracy {mean_accuracy} is outside [0, 1]; "
        "check baseline CSV integrity"
    )


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise HarnessB5InputError(
            f"Missing required artefact: {path}. Run: {SUGGESTED_COMMAND}"
        )


def load_harness_b5_alignment(
    csv_path: Path,
    *,
    paper_baseline: str = "B5",
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
) -> HarnessB5Alignment:
    """Load B5 rows from baseline CSV and classify scenario labels."""
    _require_file(csv_path)

    required_fields = {
        "paper_baseline",
        "scenario",
        "seed",
        "event_detection_accuracy",
    }
    grouped: dict[str, list[float]] = {scenario: [] for scenario in scenarios}

    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required_fields.issubset(reader.fieldnames):
            missing = required_fields - set(reader.fieldnames or ())
            raise HarnessB5InputError(
                f"{csv_path} missing columns {sorted(missing)}; regenerate via validate-tsgg"
            )

        for row in reader:
            if row["paper_baseline"] != paper_baseline:
                continue
            scenario = row["scenario"]
            if scenario not in grouped:
                continue
            try:
                accuracy = float(row["event_detection_accuracy"])
            except (TypeError, ValueError) as exc:
                raise HarnessB5InputError(
                    f"Invalid event_detection_accuracy in {csv_path} for {scenario}"
                ) from exc
            if not 0.0 <= accuracy <= 1.0:
                raise HarnessB5InputError(
                    f"event_detection_accuracy {accuracy} out of [0,1] for {scenario}"
                )
            grouped[scenario].append(accuracy)

    rows: list[HarnessB5ScenarioRow] = []
    for scenario in scenarios:
        values = grouped[scenario]
        if not values:
            raise HarnessB5InputError(
                f"No {paper_baseline} rows for scenario {scenario!r} in {csv_path}"
            )
        mean_accuracy = round(sum(values) / len(values), 4)
        rows.append(
            HarnessB5ScenarioRow(
                scenario=scenario,
                mean_detection_accuracy=mean_accuracy,
                seed_count=len(values),
                label=classify_detection_accuracy(mean_accuracy),
            )
        )

    return HarnessB5Alignment(paper_baseline=paper_baseline, rows=tuple(rows))


__all__ = [
    "FAIL_THRESHOLD",
    "HarnessB5Alignment",
    "HarnessB5InputError",
    "HarnessB5ScenarioRow",
    "PASS_THRESHOLD",
    "SUGGESTED_COMMAND",
    "classify_detection_accuracy",
    "load_harness_b5_alignment",
]
