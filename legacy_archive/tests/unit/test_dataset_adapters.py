"""Unit tests for external dataset adapters (synthetic fixtures only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dualexis.datasets import (
    DatasetId,
    DatasetRole,
    UnknownDatasetAdapterError,
    get_dataset_adapter,
    list_dataset_adapters,
)
from dualexis.datasets.adapters.dcase import DcaseAudioAdapter, DcaseRecord
from dualexis.datasets.adapters.shanghaitech import ShanghaiTechCampusAdapter
from dualexis.datasets.adapters.ucf_crime import UcfCrimeAdapter, UcfCrimeRecord
from dualexis.datasets.adapters.vadere import VadereSimulationAdapter
from dualexis.privacy_runtime.models import PrivacyLevel
from dualexis.semantic_events.models import EventSource, EventType

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "datasets"


@pytest.mark.unit
def test_list_dataset_adapters_registers_four() -> None:
    adapters = list_dataset_adapters()
    assert len(adapters) == 4
    assert DatasetId.VADERE in adapters


@pytest.mark.unit
def test_get_dataset_adapter_unknown_raises() -> None:
    with pytest.raises(UnknownDatasetAdapterError):
        get_dataset_adapter("not_a_dataset")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("dataset_id", "fixture_dir"),
    [
        (DatasetId.UCF_CRIME, "ucf_crime"),
        (DatasetId.SHANGHAITECH_CAMPUS, "shanghaitech"),
        (DatasetId.DCASE_AUDIO, "dcase"),
        (DatasetId.VADERE, "vadere"),
    ],
)
def test_adapters_convert_fixtures_to_semantic_events(
    dataset_id: DatasetId,
    fixture_dir: str,
) -> None:
    adapter = get_dataset_adapter(dataset_id)
    result = adapter.adapt(FIXTURES_ROOT / fixture_dir)
    assert result.dataset_id == dataset_id
    assert result.converted_count == len(result.events)
    assert result.converted_count >= 1
    for event in result.events:
        assert event.raw_media_persisted is False
        assert event.privacy_level is PrivacyLevel.SEMANTIC_ONLY
        assert event.explanation


@pytest.mark.unit
def test_ucf_crime_maps_known_classes() -> None:
    adapter = UcfCrimeAdapter()
    fighting = adapter.convert_record(UcfCrimeRecord("Fighting", "Fighting001_x264", 1.0, 2.0))
    assert fighting is not None
    assert fighting.event_type is EventType.CROWD_ACCELERATION
    assert fighting.source is EventSource.VIDEO_EDGE_NODE

    unknown = adapter.convert_record(UcfCrimeRecord("UnknownClass", "Clip999_x264", 0.0, 1.0))
    assert unknown is None


@pytest.mark.unit
def test_shanghaitech_skips_normal_frames() -> None:
    adapter = ShanghaiTechCampusAdapter()
    result = adapter.adapt(FIXTURES_ROOT / "shanghaitech")
    assert result.skipped_count >= 1
    assert all(event.event_type is not EventType.NORMAL_FLOW for event in result.events)


@pytest.mark.unit
def test_dcase_skips_non_stress_labels() -> None:
    adapter = DcaseAudioAdapter()
    result = adapter.adapt(FIXTURES_ROOT / "dcase")
    assert result.converted_count == 1
    assert result.events[0].event_type is EventType.AUDIO_STRESS_SIGNAL
    assert result.skipped_count == 2


@pytest.mark.unit
def test_vadere_skips_unsupported_signals() -> None:
    adapter = VadereSimulationAdapter()
    result = adapter.adapt(FIXTURES_ROOT / "vadere")
    assert result.converted_count == 2
    assert result.skipped_count == 1
    assert {event.event_type for event in result.events} == {
        EventType.EXIT_BLOCKAGE,
        EventType.CROWD_ACCELERATION,
    }


@pytest.mark.unit
def test_adapter_info_documents_roles() -> None:
    adapter = get_dataset_adapter(DatasetId.DCASE_AUDIO)
    info = adapter.adapter_info()
    assert DatasetRole.TRAINING in info.supported_roles
    assert info.annotation_only is True
    assert "identifiable" in info.privacy_risks.lower()


@pytest.mark.unit
def test_dcase_convert_record_direct() -> None:
    adapter = DcaseAudioAdapter()
    event = adapter.convert_record(DcaseRecord("clip.wav", 0.0, 5.0, "scream"))
    assert event is not None
    assert event.metadata["dataset"] == "dcase_audio"
