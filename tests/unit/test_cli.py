"""Tests for the DUALEXIS CLI and package version."""

from __future__ import annotations

import json

from typer.testing import CliRunner

import dualexis
from dualexis.cli import app
from dualexis.core.version import __version__, get_version

runner = CliRunner()


def test_import_dualexis_package() -> None:
    assert dualexis.__version__ == __version__


def test_package_version_is_defined() -> None:
    version = get_version()
    assert version
    assert version == __version__


def test_cli_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_cli_check_command_exists() -> None:
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "quality gates" in result.stdout.lower() or "Run the same" in result.stdout


def test_cli_simulate_command() -> None:
    result = runner.invoke(app, ["simulate", "--scenario", "normal_flow", "--seed", "7"])
    assert result.exit_code == 0
    assert "events=" in result.stdout


def test_cli_simulate_json_output() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--scenario", "exit_blockage", "--seed", "42", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["scenario_id"] == "exit_blockage"
    assert payload["seed"] == 42
    assert payload["event_count"] > 0
    assert payload["events"][0]["event_type"]


def test_cli_simulate_invalid_scenario() -> None:
    result = runner.invoke(app, ["simulate", "--scenario", "invalid_scenario", "--seed", "1"])
    assert result.exit_code == 1
    assert "Unknown scenario" in result.stderr or "Unknown scenario" in result.stdout
