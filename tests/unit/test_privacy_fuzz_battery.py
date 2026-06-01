"""Tests for privacy fuzz battery export."""

from __future__ import annotations

import pytest

from dualexis.evaluation.privacy_fuzz_battery import (
    default_fuzz_cases,
    export_privacy_fuzz_results,
    run_privacy_fuzz_battery,
)


@pytest.mark.unit
def test_all_default_fuzz_cases_match_expectation() -> None:
    results = run_privacy_fuzz_battery()
    for result in results:
        assert result.rejected == result.expect_rejection, result.case_id


@pytest.mark.unit
def test_export_privacy_fuzz_csv(tmp_path) -> None:
    csv_path = export_privacy_fuzz_results(tmp_path)
    assert csv_path.is_file()
    text = csv_path.read_text(encoding="utf-8")
    assert "face_embedding" in text
    assert len(default_fuzz_cases()) >= 8
