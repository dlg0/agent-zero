"""Integration tests for validate-outputs CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml
from click.testing import CliRunner

from agent_zero.cli import main as cli


@pytest.fixture
def valid_bundle(tmp_path: Path) -> Path:
    """Create a valid results bundle for testing."""
    ts_df = pd.DataFrame(
        {
            "year": [2025],
            "region": ["AUS"],
            "commodity": ["electricity"],
            "price": [50.0],
            "demand": [1000.0],
            "supply": [1000.0],
            "emissions": [500.0],
            "scenario_id": [None],
            "assumptions_id": ["test"],
            "run_id": ["test-run"],
        }
    )
    ts_df.to_parquet(tmp_path / "timeseries.parquet")

    as_df = pd.DataFrame(
        {
            "year": [2025],
            "agent_id": ["EGEN1"],
            "agent_type": ["ElectricityProducer"],
            "region": ["AUS"],
            "capacity": [100.0],
            "investment": [10.0],
            "expected_price": [55.0],
            "other_state_vars": ["{}"],
            "action": ['{"supply": {}, "invest": {}, "retire": {}, "emissions": 0.0}'],
            "action_inputs": [None],
            "state_before": [None],
            "state_after": [None],
        }
    )
    as_df.to_parquet(tmp_path / "agent_states.parquet")

    summary = {
        "run_id": "test-run",
        "created": "2025-01-01T00:00:00",
        "cumulative_emissions": 500.0,
        "average_prices": {"electricity": 50.0},
        "investment_totals": {"total": 10.0, "by_agent_type": {}},
        "peak_capacity": {"ElectricityProducer": 100.0},
        "peak_emissions": 500.0,
        "year_net_zero": None,
        "security_of_supply": {},
    }
    with open(tmp_path / "summary.json", "w") as f:
        json.dump(summary, f)

    manifest = {
        "run_id": "test-run",
        "run_timestamp": "2025-01-01T00:00:00",
        "engine_version": "0.1.0",
        "seed": 42,
        "years": [2025],
        "assumptions": {"id": "test", "hash": "abc", "version": "1.0"},
        "scenario": None,
        "schema_versions": {"results": "1.0.0"},
        "units": {},
    }
    with open(tmp_path / "manifest.yaml", "w") as f:
        yaml.safe_dump(manifest, f)

    return tmp_path


@pytest.mark.integration
class TestValidateResultsCLI:
    def test_valid_bundle_exits_zero(self, valid_bundle: Path) -> None:
        """Valid bundle should exit with code 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-outputs", str(valid_bundle)])
        assert result.exit_code == 0
        assert "Valid results bundle" in result.output

    def test_invalid_bundle_exits_one(self, tmp_path: Path) -> None:
        """Invalid bundle (empty directory) should exit with code 1."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-outputs", str(tmp_path)])
        assert result.exit_code == 1

    def test_bundle_with_warnings_exits_zero(self, valid_bundle: Path) -> None:
        """Bundle with only warnings (negative emissions) should exit with code 0."""
        ts_df = pd.read_parquet(valid_bundle / "timeseries.parquet")
        ts_df.loc[0, "emissions"] = -50.0  # CCS scenario
        ts_df.to_parquet(valid_bundle / "timeseries.parquet")

        runner = CliRunner()
        result = runner.invoke(cli, ["validate-outputs", str(valid_bundle)])
        assert result.exit_code == 0
        assert "warning" in result.output.lower()

    def test_bundle_with_errors_exits_one(self, valid_bundle: Path) -> None:
        """Bundle with errors should exit with code 1."""
        ts_df = pd.read_parquet(valid_bundle / "timeseries.parquet")
        ts_df.loc[0, "price"] = -10.0  # Invalid negative price
        ts_df.to_parquet(valid_bundle / "timeseries.parquet")

        runner = CliRunner()
        result = runner.invoke(cli, ["validate-outputs", str(valid_bundle)])
        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_nonexistent_path_fails(self) -> None:
        """Non-existent path should fail gracefully."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-outputs", "/nonexistent/path"])
        assert result.exit_code != 0
