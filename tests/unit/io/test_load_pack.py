"""Unit tests for agent_zero.io.load_pack module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from agent_zero.io.load_pack import (
    _read_table,
    load_assumptions_pack,
    load_manifest,
    load_scenario_pack,
)


class TestLoadManifest:
    """Tests for load_manifest()."""

    def test_load_manifest_reads_yaml(self, test_data_dir: Path) -> None:
        pack_dir = test_data_dir / "assumptions_packs" / "tiny-baseline"
        manifest = load_manifest(pack_dir)

        assert manifest["id"] == "tiny-baseline"
        assert manifest["type"] == "assumptions"
        assert manifest["version"] == "1.0.0"

    def test_load_manifest_scenario_pack(self, test_data_dir: Path) -> None:
        pack_dir = test_data_dir / "scenario_packs" / "tiny-scenario"
        manifest = load_manifest(pack_dir)

        assert manifest["id"] == "tiny-scenario"
        assert manifest["type"] == "scenario"
        assert manifest["base_assumptions_id"] == "tiny-baseline"


class TestReadTable:
    """Tests for _read_table()."""

    def test_read_table_csv_fallback_when_parquet_missing(self, test_data_dir: Path) -> None:
        csv_path = test_data_dir / "assumptions_packs" / "tiny-baseline" / "assumptions.csv"
        parquet_path = csv_path.with_suffix(".parquet")
        df = _read_table(parquet_path)

        assert isinstance(df, pd.DataFrame)
        assert "region" in df.columns
        assert "param" in df.columns
        assert len(df) > 0

    def test_read_table_csv_direct(self, test_data_dir: Path) -> None:
        csv_path = test_data_dir / "assumptions_packs" / "tiny-baseline" / "assumptions.csv"
        parquet_path = csv_path.with_suffix(".parquet")
        df = _read_table(parquet_path)

        assert df["region"].iloc[0] == "AUS"
        assert "electricity" in df["tech"].values

    def test_read_table_with_temp_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"
            test_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
            test_df.to_csv(csv_path, index=False)

            parquet_path = csv_path.with_suffix(".parquet")
            result = _read_table(parquet_path)

            assert list(result.columns) == ["a", "b"]
            assert len(result) == 2


class TestLoadAssumptionsPack:
    """Tests for load_assumptions_pack()."""

    def test_returns_correct_structure(self, tiny_baseline_pack: dict) -> None:
        assert "manifest" in tiny_baseline_pack
        assert "assumptions" in tiny_baseline_pack
        assert "policy" in tiny_baseline_pack
        assert "dir" in tiny_baseline_pack

    def test_manifest_is_dict(self, tiny_baseline_pack: dict) -> None:
        assert isinstance(tiny_baseline_pack["manifest"], dict)
        assert tiny_baseline_pack["manifest"]["id"] == "tiny-baseline"

    def test_assumptions_is_dataframe(self, tiny_baseline_pack: dict) -> None:
        assumptions = tiny_baseline_pack["assumptions"]
        assert isinstance(assumptions, pd.DataFrame)
        assert "region" in assumptions.columns
        assert "param" in assumptions.columns
        assert "value" in assumptions.columns

    def test_policy_is_dataframe(self, tiny_baseline_pack: dict) -> None:
        policy = tiny_baseline_pack["policy"]
        assert isinstance(policy, pd.DataFrame)

    def test_dir_is_path(self, tiny_baseline_pack: dict, test_data_dir: Path) -> None:
        expected_dir = test_data_dir / "assumptions_packs" / "tiny-baseline"
        assert tiny_baseline_pack["dir"] == expected_dir

    def test_load_from_path(self, test_data_dir: Path) -> None:
        pack_dir = test_data_dir / "assumptions_packs" / "tiny-baseline"
        pack = load_assumptions_pack(pack_dir)

        assert pack["manifest"]["type"] == "assumptions"
        assert len(pack["assumptions"]) >= 1


class TestLoadScenarioPack:
    """Tests for load_scenario_pack()."""

    def test_returns_correct_structure(self, tiny_scenario_pack: dict) -> None:
        assert "manifest" in tiny_scenario_pack
        assert "scenario" in tiny_scenario_pack
        assert "patches" in tiny_scenario_pack
        assert "dir" in tiny_scenario_pack

    def test_manifest_is_dict(self, tiny_scenario_pack: dict) -> None:
        assert isinstance(tiny_scenario_pack["manifest"], dict)
        assert tiny_scenario_pack["manifest"]["id"] == "tiny-scenario"

    def test_scenario_is_dict(self, tiny_scenario_pack: dict) -> None:
        assert isinstance(tiny_scenario_pack["scenario"], dict)

    def test_patches_is_dataframe(self, tiny_scenario_pack: dict) -> None:
        patches = tiny_scenario_pack["patches"]
        assert isinstance(patches, pd.DataFrame)
        assert "target" in patches.columns
        assert "operation" in patches.columns

    def test_dir_is_path(self, tiny_scenario_pack: dict, test_data_dir: Path) -> None:
        expected_dir = test_data_dir / "scenario_packs" / "tiny-scenario"
        assert tiny_scenario_pack["dir"] == expected_dir

    def test_load_from_path(self, test_data_dir: Path) -> None:
        pack_dir = test_data_dir / "scenario_packs" / "tiny-scenario"
        pack = load_scenario_pack(pack_dir)

        assert pack["manifest"]["type"] == "scenario"
        assert pack["manifest"]["base_assumptions_id"] == "tiny-baseline"
        assert len(pack["patches"]) >= 1
