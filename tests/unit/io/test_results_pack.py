"""Unit tests for agent_zero.post.results_pack module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
import yaml

from agent_zero.post.results_pack import UNITS, write_run_bundle
from agent_zero.utils.types import Action, AgentState, WorldState


@pytest.fixture
def synthetic_history() -> list[tuple[WorldState, list[AgentState], list[Action]]]:
    """Create a synthetic history with known values for testing."""
    history = []

    for year in [2025, 2026, 2027]:
        world = WorldState(
            t=year,
            prices={"electricity": 50.0 + year - 2025, "hydrogen": 80.0 + year - 2025},
            demand={"electricity": 1000.0, "hydrogen": 200.0},
            policy=pd.DataFrame(),
            assumptions=pd.DataFrame(),
            flows={},
            emissions=100.0 - (year - 2025) * 10,
        )

        agents = [
            AgentState(
                id="prod_1",
                agent_type="ElectricityProducer",
                region="AUS",
                sector="energy",
                tech="solar",
                capacity=100.0 + (year - 2025) * 10,
                vintage=2020,
                cash=5000.0,
                horizon=10,
                params={"efficiency": 0.95},
            ),
            AgentState(
                id="prod_2",
                agent_type="HydrogenProducer",
                region="AUS",
                sector="energy",
                tech="electrolyzer",
                capacity=50.0 + (year - 2025) * 5,
                vintage=2022,
                cash=3000.0,
                horizon=15,
                params={"conversion_rate": 0.7},
            ),
            AgentState(
                id="reg_1",
                agent_type="Regulator",
                region="AUS",
                sector=None,
                tech=None,
                capacity=0.0,
                vintage=0,
                cash=0.0,
                horizon=1,
                params={},
            ),
            AgentState(
                id="consumer_1",
                agent_type="IndustrialConsumer",
                region="AUS",
                sector="manufacturing",
                tech=None,
                capacity=0.0,
                vintage=0,
                cash=10000.0,
                horizon=5,
                params={"demand_elasticity": -0.3},
            ),
        ]

        actions = [
            Action(
                agent_id="prod_1",
                supply={"electricity": 90.0},
                invest={"solar": 10.0, "wind": 5.0},
                retire={},
                emissions=5.0,
                expected_price=52.0,
            ),
            Action(
                agent_id="prod_2",
                supply={"hydrogen": 45.0},
                invest={"electrolyzer": 5.0},
                retire={},
                emissions=2.0,
                expected_price=85.0,
            ),
            Action(
                agent_id="reg_1",
                supply={},
                invest={},
                retire={},
                emissions=0.0,
                expected_price=None,
            ),
            Action(
                agent_id="consumer_1",
                supply={},
                invest={},
                retire={},
                emissions=0.0,
                expected_price=None,
            ),
        ]

        history.append((world, agents, actions))

    return history


@pytest.fixture
def sample_manifests() -> dict[str, dict]:
    """Create sample manifest dicts for testing."""
    return {
        "assumptions": {
            "id": "baseline-v1",
            "hash": "abc123",
            "version": "1.0.0",
            "schema_version": "1.0.0",
        },
        "scenario": {
            "id": "fast-elec-v1",
            "hash": "def456",
            "version": "1.0.0",
            "schema_version": "1.0.0",
        },
    }


class TestTimeseriesParquet:
    """Tests for timeseries.parquet output."""

    def test_timeseries_has_required_columns(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ts_df = pd.read_parquet(run_dir / "timeseries.parquet")

            required_cols = [
                "year",
                "region",
                "commodity",
                "price",
                "demand",
                "supply",
                "emissions",
                "scenario_id",
                "assumptions_id",
                "run_id",
            ]
            for col in required_cols:
                assert col in ts_df.columns, f"Missing column: {col}"

    def test_timeseries_data_types(self, synthetic_history: list, sample_manifests: dict) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ts_df = pd.read_parquet(run_dir / "timeseries.parquet")

            assert pd.api.types.is_integer_dtype(ts_df["year"])
            assert pd.api.types.is_string_dtype(ts_df["region"])
            assert pd.api.types.is_string_dtype(ts_df["commodity"])
            assert pd.api.types.is_float_dtype(ts_df["price"])
            assert pd.api.types.is_float_dtype(ts_df["demand"])
            assert pd.api.types.is_float_dtype(ts_df["supply"])
            assert pd.api.types.is_float_dtype(ts_df["emissions"])

    def test_emissions_deduplicated_correctly(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """Emissions should be the same for all commodity rows in same year/region."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ts_df = pd.read_parquet(run_dir / "timeseries.parquet")

            for (year, region), group in ts_df.groupby(["year", "region"]):
                emissions_values = group["emissions"].unique()
                assert len(emissions_values) == 1, f"Multiple emissions values for {year}/{region}"

    def test_timeseries_excludes_carbon(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """Carbon price should not appear as a commodity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ts_df = pd.read_parquet(run_dir / "timeseries.parquet")

            assert "carbon" not in ts_df["commodity"].values

    def test_timeseries_ids_populated(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ts_df = pd.read_parquet(run_dir / "timeseries.parquet")

            assert (ts_df["run_id"] == "test-run").all()
            assert (ts_df["scenario_id"] == "fast-elec-v1").all()
            assert (ts_df["assumptions_id"] == "baseline-v1").all()


class TestAgentStatesParquet:
    """Tests for agent_states.parquet output."""

    def test_agent_states_has_required_columns(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ag_df = pd.read_parquet(run_dir / "agent_states.parquet")

            required_cols = [
                "year",
                "agent_id",
                "agent_type",
                "region",
                "capacity",
                "investment",
                "expected_price",
                "other_state_vars",
            ]
            for col in required_cols:
                assert col in ag_df.columns, f"Missing column: {col}"

    def test_investment_matches_action_invest_sum(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """Investment column should equal sum of Action.invest values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ag_df = pd.read_parquet(run_dir / "agent_states.parquet")

            prod1_rows = ag_df[ag_df["agent_id"] == "prod_1"]
            assert (prod1_rows["investment"] == 15.0).all()

            prod2_rows = ag_df[ag_df["agent_id"] == "prod_2"]
            assert (prod2_rows["investment"] == 5.0).all()

    def test_expected_price_for_producers(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """Producers should have non-null expected_price."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ag_df = pd.read_parquet(run_dir / "agent_states.parquet")

            producers = ag_df[ag_df["agent_type"].str.contains("Producer")]
            assert producers["expected_price"].notna().all()

    def test_expected_price_null_for_non_producers(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """Regulator and IndustrialConsumer should have null expected_price."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ag_df = pd.read_parquet(run_dir / "agent_states.parquet")

            regulator = ag_df[ag_df["agent_type"] == "Regulator"]
            assert regulator["expected_price"].isna().all()

            consumer = ag_df[ag_df["agent_type"] == "IndustrialConsumer"]
            assert consumer["expected_price"].isna().all()

    def test_other_state_vars_is_valid_json(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """other_state_vars should be valid JSON with required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ag_df = pd.read_parquet(run_dir / "agent_states.parquet")

            required_keys = {"sector", "tech", "cash", "horizon", "vintage", "params"}
            for _, row in ag_df.iterrows():
                state_vars = json.loads(row["other_state_vars"])
                assert isinstance(state_vars, dict)
                assert set(state_vars.keys()) == required_keys

    def test_other_state_vars_contains_correct_values(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """other_state_vars should contain the agent's state values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )
            ag_df = pd.read_parquet(run_dir / "agent_states.parquet")

            prod1_2025 = ag_df[(ag_df["agent_id"] == "prod_1") & (ag_df["year"] == 2025)]
            state_vars = json.loads(prod1_2025.iloc[0]["other_state_vars"])

            assert state_vars["sector"] == "energy"
            assert state_vars["tech"] == "solar"
            assert state_vars["cash"] == 5000.0
            assert state_vars["horizon"] == 10
            assert state_vars["vintage"] == 2020
            assert state_vars["params"] == {"efficiency": 0.95}


class TestSummaryJson:
    """Tests for summary.json output."""

    def test_summary_has_required_fields(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "summary.json") as f:
                summary = json.load(f)

            required_fields = [
                "run_id",
                "created",
                "cumulative_emissions",
                "average_prices",
                "investment_totals",
                "peak_capacity",
                "peak_emissions",
                "year_net_zero",
                "security_of_supply",
            ]
            for field in required_fields:
                assert field in summary, f"Missing field: {field}"

    def test_cumulative_emissions_equals_deduplicated_sum(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """cumulative_emissions should equal sum of deduplicated emissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "summary.json") as f:
                summary = json.load(f)

            expected_emissions = sum(100.0 - (y - 2025) * 10 for y in [2025, 2026, 2027])
            assert summary["cumulative_emissions"] == pytest.approx(expected_emissions)

    def test_investment_totals_structure(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """investment_totals should have 'total' and 'by_agent_type' keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "summary.json") as f:
                summary = json.load(f)

            assert "total" in summary["investment_totals"]
            assert "by_agent_type" in summary["investment_totals"]
            assert isinstance(summary["investment_totals"]["by_agent_type"], dict)

    def test_investment_totals_values(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """Verify investment totals are computed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "summary.json") as f:
                summary = json.load(f)

            expected_total = (15.0 + 5.0) * 3
            assert summary["investment_totals"]["total"] == pytest.approx(expected_total)

            by_type = summary["investment_totals"]["by_agent_type"]
            assert by_type["ElectricityProducer"] == pytest.approx(45.0)
            assert by_type["HydrogenProducer"] == pytest.approx(15.0)

    def test_average_prices_by_commodity(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "summary.json") as f:
                summary = json.load(f)

            assert "electricity" in summary["average_prices"]
            assert "hydrogen" in summary["average_prices"]
            assert summary["average_prices"]["electricity"] == pytest.approx(51.0)
            assert summary["average_prices"]["hydrogen"] == pytest.approx(81.0)

    def test_security_of_supply_structure(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "summary.json") as f:
                summary = json.load(f)

            sos = summary["security_of_supply"]
            for commodity in ["electricity", "hydrogen"]:
                assert commodity in sos
                assert "shortage_frequency" in sos[commodity]
                assert "min_supply_demand_ratio" in sos[commodity]


class TestManifestYaml:
    """Tests for manifest.yaml output."""

    def test_manifest_has_required_fields(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)

            required_fields = [
                "run_id",
                "run_timestamp",
                "engine_version",
                "seed",
                "years",
                "assumptions",
                "scenario",
                "schema_versions",
                "units",
            ]
            for field in required_fields:
                assert field in manifest, f"Missing field: {field}"

    def test_schema_versions_structure(
        self, synthetic_history: list, sample_manifests: dict
    ) -> None:
        """schema_versions should have results, assumptions, scenario keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)

            sv = manifest["schema_versions"]
            assert "results" in sv
            assert "assumptions" in sv
            assert "scenario" in sv
            assert sv["results"] == "1.0.0"

    def test_units_structure(self, synthetic_history: list, sample_manifests: dict) -> None:
        """units should have timeseries and agent_states keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)

            units = manifest["units"]
            assert "timeseries" in units
            assert "agent_states" in units
            assert units == UNITS

    def test_lineage_refs_populated(self, synthetic_history: list, sample_manifests: dict) -> None:
        """assumptions and scenario refs should contain id, hash, version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)

            assumptions_ref = manifest["assumptions"]
            assert assumptions_ref["id"] == "baseline-v1"
            assert assumptions_ref["hash"] == "abc123"
            assert assumptions_ref["version"] == "1.0.0"

            scenario_ref = manifest["scenario"]
            assert scenario_ref["id"] == "fast-elec-v1"
            assert scenario_ref["hash"] == "def456"
            assert scenario_ref["version"] == "1.0.0"

    def test_years_list(self, synthetic_history: list, sample_manifests: dict) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)

            assert manifest["years"] == [2025, 2026, 2027]

    def test_seed_preserved(self, synthetic_history: list, sample_manifests: dict) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, sample_manifests, seed=42
            )

            with open(run_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)

            assert manifest["seed"] == 42


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_no_scenario_manifest(self, synthetic_history: list) -> None:
        """Should handle missing scenario manifest gracefully."""
        manifests = {
            "assumptions": {"id": "baseline-v1", "hash": "abc", "version": "1.0.0"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "test-run", synthetic_history, manifests, seed=42
            )

            ts_df = pd.read_parquet(run_dir / "timeseries.parquet")
            assert ts_df["scenario_id"].isna().all()

            with open(run_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)
            assert manifest["scenario"] is None

    def test_empty_history(self, sample_manifests: dict) -> None:
        """Should handle empty history gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(Path(tmpdir), "test-run", [], sample_manifests, seed=42)

            ts_df = pd.read_parquet(run_dir / "timeseries.parquet")
            assert len(ts_df) == 0

            with open(run_dir / "summary.json") as f:
                summary = json.load(f)
            assert summary["cumulative_emissions"] == 0.0
            assert summary["investment_totals"]["total"] == 0.0

    def test_run_directory_created(self, synthetic_history: list, sample_manifests: dict) -> None:
        """Should create run directory with correct name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = write_run_bundle(
                Path(tmpdir), "my-run-123", synthetic_history, sample_manifests, seed=42
            )

            assert run_dir.name == "my-run-123"
            assert run_dir.exists()
            assert (run_dir / "timeseries.parquet").exists()
            assert (run_dir / "agent_states.parquet").exists()
            assert (run_dir / "summary.json").exists()
            assert (run_dir / "manifest.yaml").exists()
