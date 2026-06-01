"""Load scenario ground truth from independent YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from dualexis.orchestration.models import SeverityLevel
from dualexis.semantic_events.models import EventType
from dualexis.simulation.ground_truth import GroundTruthLabel, ScenarioGroundTruth
from dualexis.simulation.scenario import ScenarioId


class _YamlLabelRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick: int = Field(ge=0)
    zone_id: str = Field(min_length=1, max_length=64)
    semantic_label: str = Field(min_length=1, max_length=128)
    expected_severity: SeverityLevel = SeverityLevel.LOW
    expected_event_type: EventType
    notes: str = ""


class _YamlGroundTruthDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: ScenarioId
    primary_label: str = Field(min_length=1, max_length=128)
    recommended_review: bool = False
    source: str = Field(default="independent_labeler_v1")
    labels: tuple[_YamlLabelRow, ...] = Field(default_factory=tuple)


def default_ground_truth_dir() -> Path:
    """Return the repository ``experiments/ground_truth`` directory."""
    return Path(__file__).resolve().parents[2] / "experiments" / "ground_truth"


def ground_truth_path_for(scenario_id: ScenarioId, *, base_dir: Path | None = None) -> Path:
    root = base_dir or default_ground_truth_dir()
    return root / f"{scenario_id.value}.yaml"


def load_scenario_ground_truth(
    scenario_id: ScenarioId,
    *,
    base_dir: Path | None = None,
) -> ScenarioGroundTruth:
    """Load independent ground truth for a scenario from YAML."""
    path = ground_truth_path_for(scenario_id, base_dir=base_dir)
    if not path.is_file():
        msg = f"Missing independent ground-truth file: {path}"
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc = _YamlGroundTruthDocument.model_validate(raw)
    if doc.scenario_id != scenario_id:
        msg = f"Ground-truth scenario mismatch in {path}: {doc.scenario_id} != {scenario_id}"
        raise ValueError(msg)

    labels = tuple(
        GroundTruthLabel(
            scenario_id=scenario_id,
            tick=row.tick,
            zone_id=row.zone_id,
            semantic_label=row.semantic_label,
            expected_severity=row.expected_severity,
            expected_event_type=row.expected_event_type,
            notes=row.notes or doc.source,
        )
        for row in doc.labels
    )
    return ScenarioGroundTruth(
        scenario_id=scenario_id,
        primary_label=doc.primary_label,
        labels=labels,
        recommended_review=doc.recommended_review,
    )


def dump_scenario_ground_truth_yaml(
    ground_truth: ScenarioGroundTruth,
    *,
    base_dir: Path | None = None,
    source: str = "independent_labeler_v1",
) -> Path:
    """Write a ground-truth document to the standard experiments directory."""
    path = ground_truth_path_for(ground_truth.scenario_id, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scenario_id": ground_truth.scenario_id.value,
        "primary_label": ground_truth.primary_label,
        "recommended_review": ground_truth.recommended_review,
        "source": source,
        "labels": [
            {
                "tick": label.tick,
                "zone_id": label.zone_id,
                "semantic_label": label.semantic_label,
                "expected_severity": label.expected_severity.value,
                "expected_event_type": label.expected_event_type.value,
                "notes": label.notes,
            }
            for label in ground_truth.labels
        ],
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


__all__ = [
    "default_ground_truth_dir",
    "dump_scenario_ground_truth_yaml",
    "ground_truth_path_for",
    "load_scenario_ground_truth",
]
