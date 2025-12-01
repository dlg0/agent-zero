"""Unit tests for agent_zero.post.export_web module."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from agent_zero.post.export_web import (
    _build_reproduction_command,
    _convert_manifest,
    _determine_action,
    _extract_agent_traces,
    _extract_agents,
    export_web_bundle,
    rebuild_web_index,
)

# --- Shape validators for TypeScript type compatibility ---


def _assert_manifest_shape(m: dict) -> None:
    """Assert manifest.json matches expected TypeScript Manifest type."""
    assert isinstance(m.get("run_id"), str), "run_id must be string"
    assert isinstance(m.get("created_at"), str), "created_at must be string"
    assert isinstance(m.get("engine_version"), str), "engine_version must be string"
    assert isinstance(m.get("years"), dict), "years must be dict"
    assert "start" in m["years"] and "end" in m["years"], "years must have start and end"
    assert isinstance(m.get("assumptions"), dict), "assumptions must be dict"
    assert "id" in m["assumptions"], "assumptions must have id"
    scenario = m.get("scenario")
    if scenario is not None:
        assert isinstance(scenario, dict) and "id" in scenario


def _assert_summary_shape(s: dict) -> None:
    """Assert summary.json matches expected TypeScript Summary type."""
    assert isinstance(s.get("run_id"), str), "run_id must be string"
    assert "cumulative_emissions" in s or "total_emissions" in s
    assert "peak_emissions" in s
    assert "year_net_zero" in s


def _assert_timeseries_shape(rows: list) -> None:
    """Assert timeseries.json matches expected TypeScript Timeseries type."""
    for row in rows:
        assert "year" in row, "timeseries row must have year"
        assert "region" in row, "timeseries row must have region"
        assert "commodity" in row, "timeseries row must have commodity"
        assert "price" in row, "timeseries row must have price"
        assert "demand" in row, "timeseries row must have demand"
        assert "supply" in row, "timeseries row must have supply"


def _assert_agents_shape(agents: list) -> None:
    """Assert agents.json matches expected TypeScript Agents type."""
    for a in agents:
        assert "agent_id" in a, "agent must have agent_id"
        assert "agent_type" in a, "agent must have agent_type"
        assert "region" in a, "agent must have region"
        assert "initial_capacity" in a, "agent must have initial_capacity"


def _assert_agent_traces_shape(traces: list) -> None:
    """Assert agent_traces.json matches expected TypeScript AgentTraces type."""
    for t in traces:
        assert "agent_id" in t, "trace must have agent_id"
        assert "year" in t, "trace must have year"
        assert "action" in t, "trace must have action"


def _assert_assumptions_used_shape(rows: list) -> None:
    """Assert assumptions_used.json matches expected TypeScript AssumptionsUsed type."""
    for row in rows:
        assert "param" in row, "assumption row must have param"
        assert "year" in row, "assumption row must have year"
        assert "value" in row, "assumption row must have value"
        assert "unit" in row, "assumption row must have unit"


def _assert_drivers_shape(drivers: list) -> None:
    """Assert drivers.json matches expected TypeScript Drivers type."""
    for d in drivers:
        assert "factor" in d, "driver must have factor"
        assert "direction" in d, "driver must have direction"
        assert isinstance(d.get("related_params", []), list)
        assert isinstance(d.get("related_agents", []), list)


@pytest.fixture
def sample_manifest() -> dict:
    """Create a sample manifest for testing."""
    return {
        "run_id": "test-run-123",
        "run_timestamp": "2024-11-30T10:15:30.000Z",
        "engine_version": "0.1.0",
        "seed": 42,
        "years": [2025, 2026, 2027],
        "assumptions": {
            "id": "baseline-v1",
            "hash": "abc123",
            "version": "1.0.0",
        },
        "scenario": {
            "id": "fast-elec-v1",
            "hash": "def456",
            "version": "1.0.0",
        },
        "schema_versions": {
            "assumptions": "1.0.0",
            "scenario": "1.0.0",
            "results": "1.0.0",
        },
        "units": {
            "timeseries": {"year": None, "price": "USD/MWh"},
            "agent_states": {"year": None, "capacity": "MW"},
        },
    }


@pytest.fixture
def sample_run_dir(tmp_path: Path, sample_manifest: dict) -> Path:
    """Create a sample run directory for testing."""
    run_dir = tmp_path / "test-run-123"
    run_dir.mkdir()

    with (run_dir / "manifest.yaml").open("w") as f:
        yaml.safe_dump(sample_manifest, f)

    summary = {
        "run_id": "test-run-123",
        "created": "2024-11-30T10:15:30.000Z",
        "cumulative_emissions": 1000000.0,
        "peak_emissions": 500000.0,
        "year_net_zero": 2045,
    }
    with (run_dir / "summary.json").open("w") as f:
        json.dump(summary, f)

    ts_df = pd.DataFrame(
        [
            {
                "year": 2025,
                "region": "AUS",
                "commodity": "electricity",
                "price": 50.0,
                "demand": 1000.0,
                "supply": 1100.0,
                "emissions": 500000.0,
                "scenario_id": "fast-elec-v1",
                "assumptions_id": "baseline-v1",
                "run_id": "test-run-123",
            },
            {
                "year": 2026,
                "region": "AUS",
                "commodity": "electricity",
                "price": 48.0,
                "demand": 1050.0,
                "supply": 1150.0,
                "emissions": 450000.0,
                "scenario_id": "fast-elec-v1",
                "assumptions_id": "baseline-v1",
                "run_id": "test-run-123",
            },
        ]
    )
    ts_df.to_parquet(run_dir / "timeseries.parquet", index=False)

    ag_df = pd.DataFrame(
        [
            {
                "year": 2025,
                "agent_id": "EGEN1",
                "agent_type": "ElectricityProducer",
                "region": "AUS",
                "capacity": 100.0,
                "investment": 10.0,
                "expected_price": 52.0,
                "other_state_vars": json.dumps(
                    {
                        "sector": None,
                        "tech": "electricity",
                        "cash": 5000.0,
                        "horizon": 3,
                        "vintage": 2024,
                        "params": {},
                    }
                ),
                "action": json.dumps(
                    {
                        "supply": {"electricity": 90.0},
                        "invest": {"solar": 10.0},
                        "retire": {},
                        "emissions": 5.0,
                    }
                ),
                "action_inputs": json.dumps(
                    {"current_price": 50.0, "npv": 1000.0, "carbon_price": 25.0}
                ),
                "state_before": json.dumps({"capacity": 90.0, "cash": 4000.0, "vintage": 2024}),
                "state_after": json.dumps({"capacity": 100.0, "cash": 5000.0, "vintage": 2024}),
            },
            {
                "year": 2026,
                "agent_id": "EGEN1",
                "agent_type": "ElectricityProducer",
                "region": "AUS",
                "capacity": 110.0,
                "investment": 10.0,
                "expected_price": 50.0,
                "other_state_vars": json.dumps(
                    {
                        "sector": None,
                        "tech": "electricity",
                        "cash": 6000.0,
                        "horizon": 3,
                        "vintage": 2024,
                        "params": {},
                    }
                ),
                "action": json.dumps(
                    {
                        "supply": {"electricity": 100.0},
                        "invest": {"solar": 10.0},
                        "retire": {},
                        "emissions": 4.5,
                    }
                ),
                "action_inputs": json.dumps(
                    {"current_price": 48.0, "npv": 1200.0, "carbon_price": 30.0}
                ),
                "state_before": json.dumps({"capacity": 100.0, "cash": 5000.0, "vintage": 2024}),
                "state_after": json.dumps({"capacity": 110.0, "cash": 6000.0, "vintage": 2024}),
            },
        ]
    )
    ag_df.to_parquet(run_dir / "agent_states.parquet", index=False)

    return run_dir


class TestBuildReproductionCommand:
    """Tests for _build_reproduction_command."""

    def test_basic_command(self) -> None:
        manifest = {
            "assumptions": {"id": "baseline"},
            "years": {"start": 2024, "end": 2050},
            "seed": 42,
        }
        cmd = _build_reproduction_command(manifest)
        assert cmd == "agentzero run --assum baseline --years 2024:2050 --seed 42"

    def test_with_scenario(self) -> None:
        manifest = {
            "assumptions": {"id": "baseline"},
            "scenario": {"id": "high_growth"},
            "years": {"start": 2024, "end": 2050},
            "seed": 0,
        }
        cmd = _build_reproduction_command(manifest)
        assert "--scen high_growth" in cmd

    def test_years_as_list(self) -> None:
        manifest = {
            "assumptions": {"id": "baseline"},
            "years": [2025, 2026, 2027, 2028],
            "seed": 0,
        }
        cmd = _build_reproduction_command(manifest)
        assert "--years 2025,2026,2027,2028" in cmd

    def test_years_with_step(self) -> None:
        manifest = {
            "assumptions": {"id": "baseline"},
            "years": {"start": 2024, "end": 2050, "step": 5},
            "seed": 0,
        }
        cmd = _build_reproduction_command(manifest)
        assert "--years 2024:5:2050" in cmd

    def test_no_scenario(self) -> None:
        manifest = {
            "assumptions": {"id": "baseline"},
            "years": {"start": 2024, "end": 2050},
        }
        cmd = _build_reproduction_command(manifest)
        assert "--scen" not in cmd


class TestConvertManifest:
    """Tests for _convert_manifest."""

    def test_basic_conversion(self, sample_manifest: dict) -> None:
        result = _convert_manifest(sample_manifest, "test-run-123")
        assert result["run_id"] == "test-run-123"
        assert result["engine_version"] == "0.1.0"
        assert result["years"] == {"start": 2025, "end": 2027}
        assert result["seed"] == 42

    def test_assumptions_structure(self, sample_manifest: dict) -> None:
        result = _convert_manifest(sample_manifest, "test-run-123")
        assert result["assumptions"]["id"] == "baseline-v1"
        assert result["assumptions"]["version"] == "1.0.0"
        assert result["assumptions"]["hash"] == "abc123"

    def test_scenario_structure(self, sample_manifest: dict) -> None:
        result = _convert_manifest(sample_manifest, "test-run-123")
        assert result["scenario"]["id"] == "fast-elec-v1"
        assert result["scenario"]["version"] == "1.0.0"

    def test_no_scenario(self) -> None:
        manifest = {
            "run_id": "test",
            "assumptions": {"id": "baseline"},
            "years": [2025],
        }
        result = _convert_manifest(manifest, "test")
        assert result["scenario"] is None

    def test_reproduction_command_generated(self, sample_manifest: dict) -> None:
        result = _convert_manifest(sample_manifest, "test-run-123")
        assert "agentzero run" in result["reproduction_command"]
        assert "--assum baseline-v1" in result["reproduction_command"]

    def test_reproduction_command_uses_stored_cli_command(self, sample_manifest: dict) -> None:
        """When cli_command is stored in manifest, use it instead of reconstructing."""
        sample_manifest["cli_command"] = "uv run agentzero run --assum foo --years 2025:2030"
        result = _convert_manifest(sample_manifest, "test-run-123")
        assert (
            result["reproduction_command"] == "uv run agentzero run --assum foo --years 2025:2030"
        )


class TestExtractAgents:
    """Tests for _extract_agents."""

    def test_extracts_unique_agents(self, sample_run_dir: Path) -> None:
        ag_df = pd.read_parquet(sample_run_dir / "agent_states.parquet")
        agents = _extract_agents(ag_df)
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "EGEN1"

    def test_agent_structure(self, sample_run_dir: Path) -> None:
        ag_df = pd.read_parquet(sample_run_dir / "agent_states.parquet")
        agents = _extract_agents(ag_df)
        agent = agents[0]

        assert "agent_id" in agent
        assert "agent_type" in agent
        assert "region" in agent
        assert "initial_capacity" in agent
        assert "horizon" in agent
        assert "discount_rate" in agent
        assert "decision_rule" in agent
        assert "vintage" in agent
        assert "params" in agent

    def test_empty_dataframe(self) -> None:
        agents = _extract_agents(pd.DataFrame())
        assert agents == []


class TestExtractAgentTraces:
    """Tests for _extract_agent_traces."""

    def test_extracts_all_traces(self, sample_run_dir: Path) -> None:
        ag_df = pd.read_parquet(sample_run_dir / "agent_states.parquet")
        traces = _extract_agent_traces(ag_df)
        assert len(traces) == 2

    def test_trace_structure(self, sample_run_dir: Path) -> None:
        ag_df = pd.read_parquet(sample_run_dir / "agent_states.parquet")
        traces = _extract_agent_traces(ag_df)
        trace = traces[0]

        assert "agent_id" in trace
        assert "year" in trace
        assert "action" in trace
        assert "action_inputs" in trace
        assert "state_before" in trace
        assert "state_after" in trace

    def test_action_inputs_structure(self, sample_run_dir: Path) -> None:
        ag_df = pd.read_parquet(sample_run_dir / "agent_states.parquet")
        traces = _extract_agent_traces(ag_df)
        action_inputs = traces[0]["action_inputs"]

        assert "current_price" in action_inputs
        assert "expected_price" in action_inputs
        assert "npv" in action_inputs
        assert "carbon_price" in action_inputs

    def test_empty_dataframe(self) -> None:
        traces = _extract_agent_traces(pd.DataFrame())
        assert traces == []


class TestDetermineAction:
    """Tests for _determine_action."""

    def test_invest_action(self) -> None:
        action_data = {"invest": {"solar": 10.0}, "supply": {}, "retire": {}}
        assert _determine_action(action_data) == "invest"

    def test_retire_action(self) -> None:
        action_data = {"invest": {}, "supply": {}, "retire": {"coal": 50.0}}
        assert _determine_action(action_data) == "retire"

    def test_supply_action(self) -> None:
        action_data = {"invest": {}, "supply": {"electricity": 100.0}, "retire": {}}
        assert _determine_action(action_data) == "supply"

    def test_hold_action(self) -> None:
        action_data = {"invest": {}, "supply": {}, "retire": {}}
        assert _determine_action(action_data) == "hold"

    def test_invest_takes_precedence(self) -> None:
        action_data = {"invest": {"solar": 10.0}, "supply": {"electricity": 100.0}, "retire": {}}
        assert _determine_action(action_data) == "invest"


class TestExportWebBundle:
    """Tests for export_web_bundle."""

    def test_creates_output_directory(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output" / "nested"
        export_web_bundle(sample_run_dir, out_dir)
        assert out_dir.exists()

    def test_creates_manifest_json(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)
        assert (out_dir / "manifest.json").exists()

        with (out_dir / "manifest.json").open() as f:
            manifest = json.load(f)
        assert manifest["run_id"] == "test-run-123"

    def test_creates_summary_json(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)
        assert (out_dir / "summary.json").exists()

    def test_creates_timeseries_json(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)
        assert (out_dir / "timeseries.json").exists()

        with (out_dir / "timeseries.json").open() as f:
            timeseries = json.load(f)
        assert len(timeseries) == 2
        assert timeseries[0]["year"] == 2025

    def test_creates_agents_json(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)
        assert (out_dir / "agents.json").exists()

        with (out_dir / "agents.json").open() as f:
            agents = json.load(f)
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "EGEN1"

    def test_creates_agent_traces_json(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)
        assert (out_dir / "agent_traces.json").exists()

        with (out_dir / "agent_traces.json").open() as f:
            traces = json.load(f)
        assert len(traces) == 2

    def test_creates_placeholder_files(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)

        assert (out_dir / "assumptions_used.json").exists()
        assert (out_dir / "drivers.json").exists()

        with (out_dir / "drivers.json").open() as f:
            assert json.load(f) == []

    def test_scenario_run_creates_scenario_diff(self, sample_run_dir: Path, tmp_path: Path) -> None:
        """Scenario runs should create scenario_diff.json."""
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)

        assert (out_dir / "scenario_diff.json").exists()
        with (out_dir / "scenario_diff.json").open() as f:
            assert json.load(f) == []

    def test_baseline_run_no_scenario_diff(self, tmp_path: Path) -> None:
        """Baseline runs (no scenario) should NOT create scenario_diff.json."""
        run_dir = tmp_path / "baseline-run"
        run_dir.mkdir()

        manifest = {
            "run_id": "baseline-run",
            "assumptions": {"id": "baseline-v1", "hash": "abc123", "version": "1.0.0"},
            "scenario": None,
            "years": [2025, 2026],
            "seed": 42,
        }
        with (run_dir / "manifest.yaml").open("w") as f:
            yaml.safe_dump(manifest, f)

        with (run_dir / "summary.json").open("w") as f:
            json.dump({"run_id": "baseline-run"}, f)

        pd.DataFrame().to_parquet(run_dir / "timeseries.parquet", index=False)
        pd.DataFrame().to_parquet(run_dir / "agent_states.parquet", index=False)

        out_dir = tmp_path / "web_output"
        export_web_bundle(run_dir, out_dir)

        assert not (out_dir / "scenario_diff.json").exists()

    def test_creates_downloads_directory(self, sample_run_dir: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)

        downloads = out_dir / "downloads"
        assert downloads.exists()
        assert (downloads / "timeseries.parquet").exists() or (
            downloads / "timeseries.parquet"
        ).is_symlink()
        assert (downloads / "agent_states.parquet").exists() or (
            downloads / "agent_states.parquet"
        ).is_symlink()

    def test_raises_on_missing_manifest(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()
        out_dir = tmp_path / "web_output"

        with pytest.raises(FileNotFoundError, match=r"manifest\.yaml not found"):
            export_web_bundle(run_dir, out_dir)

    def test_exported_json_shapes_match_typescript_types(
        self, sample_run_dir: Path, tmp_path: Path
    ) -> None:
        """Test that all exported JSON files match their TypeScript type definitions."""
        out_dir = tmp_path / "web_output"
        export_web_bundle(sample_run_dir, out_dir)

        with (out_dir / "manifest.json").open() as f:
            _assert_manifest_shape(json.load(f))

        with (out_dir / "summary.json").open() as f:
            _assert_summary_shape(json.load(f))

        with (out_dir / "timeseries.json").open() as f:
            _assert_timeseries_shape(json.load(f))

        with (out_dir / "agents.json").open() as f:
            _assert_agents_shape(json.load(f))

        with (out_dir / "agent_traces.json").open() as f:
            _assert_agent_traces_shape(json.load(f))

        with (out_dir / "assumptions_used.json").open() as f:
            _assert_assumptions_used_shape(json.load(f))

        with (out_dir / "drivers.json").open() as f:
            _assert_drivers_shape(json.load(f))


class TestRebuildWebIndex:
    """Tests for rebuild_web_index."""

    def test_creates_empty_index_for_empty_dir(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        rebuild_web_index(runs_dir)

        index_path = runs_dir / "index.json"
        assert index_path.exists()
        with index_path.open() as f:
            assert json.load(f) == []

    def test_creates_index_with_runs(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        run1 = runs_dir / "run-001"
        run1.mkdir()
        manifest1 = {
            "run_id": "run-001",
            "created_at": "2024-11-30T10:00:00Z",
            "years": {"start": 2024, "end": 2050},
            "assumptions": {"id": "baseline"},
            "scenario": None,
            "engine_version": "0.1.0",
        }
        with (run1 / "manifest.json").open("w") as f:
            json.dump(manifest1, f)
        with (run1 / "summary.json").open("w") as f:
            json.dump({"cumulative_emissions": 1000000, "year_net_zero": 2045}, f)

        run2 = runs_dir / "run-002"
        run2.mkdir()
        manifest2 = {
            "run_id": "run-002",
            "created_at": "2024-11-30T11:00:00Z",
            "years": {"start": 2024, "end": 2050},
            "assumptions": {"id": "baseline"},
            "scenario": {"id": "high_growth"},
            "engine_version": "0.1.0",
        }
        with (run2 / "manifest.json").open("w") as f:
            json.dump(manifest2, f)
        with (run2 / "summary.json").open("w") as f:
            json.dump({"cumulative_emissions": 800000, "year_net_zero": 2040}, f)

        rebuild_web_index(runs_dir)

        index_path = runs_dir / "index.json"
        with index_path.open() as f:
            index = json.load(f)

        assert len(index) == 2
        assert index[0]["run_id"] == "run-002"
        assert index[1]["run_id"] == "run-001"

    def test_index_entry_structure(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        run_dir = runs_dir / "run-001"
        run_dir.mkdir()
        manifest = {
            "run_id": "run-001",
            "created_at": "2024-11-30T10:00:00Z",
            "years": {"start": 2024, "end": 2050},
            "assumptions": {"id": "baseline"},
            "scenario": {"id": "high_growth"},
            "engine_version": "0.1.0",
        }
        with (run_dir / "manifest.json").open("w") as f:
            json.dump(manifest, f)
        with (run_dir / "summary.json").open("w") as f:
            json.dump({"cumulative_emissions": 1000000, "year_net_zero": 2045}, f)

        rebuild_web_index(runs_dir)

        with (runs_dir / "index.json").open() as f:
            index = json.load(f)

        entry = index[0]
        assert entry["run_id"] == "run-001"
        assert entry["created_at"] == "2024-11-30T10:00:00Z"
        assert entry["years"] == {"start": 2024, "end": 2050}
        assert entry["assumptions_id"] == "baseline"
        assert entry["scenario_id"] == "high_growth"
        assert entry["engine_version"] == "0.1.0"
        assert entry["quick_summary"]["cumulative_emissions"] == 1000000
        assert entry["quick_summary"]["year_net_zero"] == 2045
        assert "scenario" in entry["tags"]

    def test_baseline_tag(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        run_dir = runs_dir / "run-baseline"
        run_dir.mkdir()
        manifest = {
            "run_id": "run-baseline",
            "created_at": "2024-11-30T10:00:00Z",
            "years": {"start": 2024, "end": 2050},
            "assumptions": {"id": "baseline"},
            "scenario": None,
            "engine_version": "0.1.0",
        }
        with (run_dir / "manifest.json").open("w") as f:
            json.dump(manifest, f)

        rebuild_web_index(runs_dir)

        with (runs_dir / "index.json").open() as f:
            index = json.load(f)

        assert "baseline" in index[0]["tags"]
        assert "scenario" not in index[0]["tags"]

    def test_skips_non_directories(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        (runs_dir / "readme.txt").write_text("ignore me")

        rebuild_web_index(runs_dir)

        with (runs_dir / "index.json").open() as f:
            assert json.load(f) == []

    def test_skips_dirs_without_manifest(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        (runs_dir / "incomplete-run").mkdir()

        rebuild_web_index(runs_dir)

        with (runs_dir / "index.json").open() as f:
            assert json.load(f) == []
