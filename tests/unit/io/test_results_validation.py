"""Tests for results_validation module."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from agent_zero.post.results_validation import (
    ValidationIssue,
    _load_schema,
    validate_agent_states,
    validate_bundle,
    validate_manifest,
    validate_summary,
    validate_timeseries,
)


@pytest.fixture
def schema() -> dict:
    """Load the results schema."""
    return _load_schema()


@pytest.fixture
def valid_timeseries_df() -> pd.DataFrame:
    """Create a valid timeseries DataFrame."""
    return pd.DataFrame(
        {
            "year": [2025, 2025],
            "region": ["AUS", "AUS"],
            "commodity": ["electricity", "hydrogen"],
            "price": [50.0, 100.0],
            "demand": [1000.0, 100.0],
            "supply": [1000.0, 100.0],
            "emissions": [500.0, 500.0],
            "scenario_id": [None, None],
            "assumptions_id": ["test-assumptions", "test-assumptions"],
            "run_id": ["test-run", "test-run"],
        }
    )


class TestValidateTimeseries:
    def test_valid_dataframe(self, schema: dict, valid_timeseries_df: pd.DataFrame) -> None:
        """Valid DataFrame should produce no errors."""
        issues = validate_timeseries(valid_timeseries_df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert len(errors) == 0

    def test_missing_column(self, schema: dict, valid_timeseries_df: pd.DataFrame) -> None:
        """Missing required column should produce error."""
        df = valid_timeseries_df.drop(columns=["supply"])
        issues = validate_timeseries(df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("supply" in i.message for i in errors)

    def test_negative_price_error(self, schema: dict, valid_timeseries_df: pd.DataFrame) -> None:
        """Negative price should produce error."""
        df = valid_timeseries_df.copy()
        df.loc[0, "price"] = -10.0
        issues = validate_timeseries(df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("price" in i.location for i in errors)

    def test_negative_demand_error(self, schema: dict, valid_timeseries_df: pd.DataFrame) -> None:
        """Negative demand should produce error."""
        df = valid_timeseries_df.copy()
        df.loc[0, "demand"] = -100.0
        issues = validate_timeseries(df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("demand" in i.location for i in errors)

    def test_negative_supply_error(self, schema: dict, valid_timeseries_df: pd.DataFrame) -> None:
        """Negative supply should produce error."""
        df = valid_timeseries_df.copy()
        df.loc[0, "supply"] = -50.0
        issues = validate_timeseries(df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("supply" in i.location for i in errors)

    def test_negative_emissions_warning(
        self, schema: dict, valid_timeseries_df: pd.DataFrame
    ) -> None:
        """Negative emissions should produce warning, not error."""
        df = valid_timeseries_df.copy()
        df.loc[0, "emissions"] = -50.0  # CCS scenario
        issues = validate_timeseries(df, schema)
        warnings = [i for i in issues if i.level == "warning"]
        errors = [i for i in issues if i.level == "error" and "emissions" in i.location]
        assert len(warnings) >= 1
        assert len(errors) == 0


class TestValidateAgentStates:
    @pytest.fixture
    def valid_agent_states_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "year": [2025],
                "agent_id": ["EGEN1"],
                "agent_type": ["ElectricityProducer"],
                "region": ["AUS"],
                "capacity": [100.0],
                "investment": [10.0],
                "expected_price": [55.0],
                "other_state_vars": ['{"tech": "electricity"}'],
                "action": [
                    '{"supply": {"electricity": 100.0}, "invest": {}, "retire": {}, "emissions": 0.0}'
                ],
                "action_inputs": ['{"prices": {"electricity": 50.0}}'],
                "state_before": ['{"capacity": 100.0}'],
                "state_after": ['{"capacity": 110.0}'],
            }
        )

    def test_valid_dataframe(self, schema: dict, valid_agent_states_df: pd.DataFrame) -> None:
        issues = validate_agent_states(valid_agent_states_df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert len(errors) == 0

    def test_missing_column(self, schema: dict, valid_agent_states_df: pd.DataFrame) -> None:
        """Missing required column should produce error."""
        df = valid_agent_states_df.drop(columns=["capacity"])
        issues = validate_agent_states(df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("capacity" in i.message for i in errors)

    def test_negative_capacity_error(
        self, schema: dict, valid_agent_states_df: pd.DataFrame
    ) -> None:
        df = valid_agent_states_df.copy()
        df.loc[0, "capacity"] = -10.0
        issues = validate_agent_states(df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("capacity" in i.location for i in errors)

    def test_negative_investment_error(
        self, schema: dict, valid_agent_states_df: pd.DataFrame
    ) -> None:
        df = valid_agent_states_df.copy()
        df.loc[0, "investment"] = -5.0
        issues = validate_agent_states(df, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("investment" in i.location for i in errors)


class TestValidateSummary:
    @pytest.fixture
    def valid_summary(self) -> dict:
        return {
            "run_id": "test-run",
            "created": "2025-01-01T00:00:00",
            "cumulative_emissions": 1000.0,
            "average_prices": {"electricity": 50.0},
            "investment_totals": {"total": 100.0, "by_agent_type": {}},
            "peak_capacity": {"ElectricityProducer": 200.0},
            "peak_emissions": 500.0,
            "year_net_zero": 2050,
            "security_of_supply": {},
        }

    def test_valid_summary(self, schema: dict, valid_summary: dict) -> None:
        issues = validate_summary(valid_summary, schema)
        errors = [i for i in issues if i.level == "error"]
        assert len(errors) == 0

    def test_missing_field(self, schema: dict, valid_summary: dict) -> None:
        del valid_summary["cumulative_emissions"]
        issues = validate_summary(valid_summary, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("cumulative_emissions" in i.message for i in errors)

    def test_wrong_type(self, schema: dict, valid_summary: dict) -> None:
        valid_summary["cumulative_emissions"] = "not a float"
        issues = validate_summary(valid_summary, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("cumulative_emissions" in i.location for i in errors)

    def test_null_year_net_zero_allowed(self, schema: dict, valid_summary: dict) -> None:
        """year_net_zero can be null (no net zero achieved)."""
        valid_summary["year_net_zero"] = None
        issues = validate_summary(valid_summary, schema)
        errors = [i for i in issues if i.level == "error" and "year_net_zero" in i.location]
        assert len(errors) == 0


class TestValidateManifest:
    @pytest.fixture
    def valid_manifest(self) -> dict:
        return {
            "run_id": "test-run",
            "run_timestamp": "2025-01-01T00:00:00",
            "engine_version": "0.1.0",
            "seed": 42,
            "years": [2025, 2026],
            "assumptions": {"id": "test", "hash": "abc", "version": "1.0"},
            "scenario": None,
            "schema_versions": {"results": "1.0.0"},
            "units": {},
        }

    def test_valid_manifest(self, schema: dict, valid_manifest: dict) -> None:
        issues = validate_manifest(valid_manifest, schema)
        errors = [i for i in issues if i.level == "error"]
        assert len(errors) == 0

    def test_missing_field(self, schema: dict, valid_manifest: dict) -> None:
        del valid_manifest["engine_version"]
        issues = validate_manifest(valid_manifest, schema)
        errors = [i for i in issues if i.level == "error"]
        assert any("engine_version" in i.message for i in errors)

    def test_null_seed_allowed(self, schema: dict, valid_manifest: dict) -> None:
        """seed can be null."""
        valid_manifest["seed"] = None
        issues = validate_manifest(valid_manifest, schema)
        errors = [i for i in issues if i.level == "error" and "seed" in i.location]
        assert len(errors) == 0

    def test_null_scenario_allowed(self, schema: dict, valid_manifest: dict) -> None:
        """scenario can be null (no scenario applied)."""
        valid_manifest["scenario"] = None
        issues = validate_manifest(valid_manifest, schema)
        errors = [i for i in issues if i.level == "error" and "scenario" in i.location]
        assert len(errors) == 0


class TestValidateBundle:
    def test_missing_files(self, tmp_path: Path) -> None:
        """Empty directory should produce errors for all missing files."""
        issues = validate_bundle(tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert len(errors) >= 4  # timeseries, agent_states, summary, manifest

    def test_valid_bundle(self, tmp_path: Path) -> None:
        """A valid bundle should produce no errors."""
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

        issues = validate_bundle(tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert len(errors) == 0

    def test_csv_files_accepted(self, tmp_path: Path) -> None:
        """Bundle should accept CSV files as alternative to parquet."""
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
        ts_df.to_csv(tmp_path / "timeseries.csv", index=False)

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
        as_df.to_csv(tmp_path / "agent_states.csv", index=False)

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

        issues = validate_bundle(tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert len(errors) == 0


class TestValidationIssue:
    def test_validation_issue_attributes(self) -> None:
        """ValidationIssue should have correct attributes."""
        issue = ValidationIssue(level="error", location="timeseries.price", message="Bad value")
        assert issue.level == "error"
        assert issue.location == "timeseries.price"
        assert issue.message == "Bad value"

    def test_warning_level(self) -> None:
        """Warning level should be supported."""
        issue = ValidationIssue(
            level="warning", location="timeseries.emissions", message="Negative emissions"
        )
        assert issue.level == "warning"


class TestLoadSchema:
    def test_schema_loads(self) -> None:
        """Schema should load successfully."""
        schema = _load_schema()
        assert isinstance(schema, dict)
        assert "timeseries" in schema
        assert "agent_states" in schema
        assert "summary" in schema
        assert "manifest" in schema
