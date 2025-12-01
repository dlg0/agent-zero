"""End-to-end tests for the AgentZero CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from agent_zero.cli import main


@pytest.mark.e2e
def test_cli_help() -> None:
    """Verify --help shows usage info."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "AgentZero:" in result.output
    assert "validate" in result.output
    assert "runs" in result.output


@pytest.mark.e2e
def test_validate_command_assumptions_pack(data_dir: Path) -> None:
    """Validate the baseline-v1 assumptions pack."""
    runner = CliRunner()
    pack_path = data_dir / "assumptions_packs" / "baseline-v1"
    result = runner.invoke(main, ["validate", str(pack_path)])
    assert result.exit_code == 0
    assert "Pack is valid" in result.output


@pytest.mark.e2e
def test_validate_command_scenario_pack(data_dir: Path) -> None:
    """Validate the fast-elec-v1 scenario pack."""
    runner = CliRunner()
    pack_path = data_dir / "scenario_packs" / "fast-elec-v1"
    result = runner.invoke(main, ["validate", str(pack_path)])
    assert result.exit_code == 0
    assert "Pack is valid" in result.output


@pytest.mark.e2e
def test_runs_command_no_runs(repo_root: Path) -> None:
    """Test the runs list command with no runs directory."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["runs"])
        assert result.exit_code == 0
        assert "No runs directory found" in result.output
