"""Unit tests for agent_zero.story.tools module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from agent_zero.story.tool_definitions import get_tool_by_name, get_tool_definitions
from agent_zero.story.tools import (
    compare_scenarios,
    explain_agent_behaviour,
    get_agent_summary,
    get_caveats,
    get_drivers,
    get_headline_metrics,
    get_story_context,
    to_dict,
)
from agent_zero.story.types import (
    AgentSummary,
    Caveats,
    Driver,
    HeadlineMetrics,
    ScenarioComparison,
    StoryContext,
)


@pytest.fixture
def sample_run_dir(tmp_path: Path) -> Path:
    """Create a sample run directory with all required files."""
    run_dir = tmp_path / "test-run-123"
    run_dir.mkdir()

    manifest = {
        "run_id": "test-run-123",
        "engine_version": "0.1.0",
        "seed": 42,
        "years": {"start": 2025, "end": 2030},
        "assumptions": {
            "id": "baseline-v1",
            "hash": "abc123",
            "version": "1.0.0",
        },
        "scenario": {
            "id": "fast-elec-v1",
            "hash": "def456",
            "version": "1.0.0",
            "description": "Fast electrification scenario",
        },
    }
    with (run_dir / "manifest.json").open("w") as f:
        json.dump(manifest, f)

    summary = {
        "run_id": "test-run-123",
        "created": "2024-11-30T10:15:30.000Z",
        "cumulative_emissions": 1000000.0,
        "peak_emissions": 500000.0,
        "year_net_zero": 2045,
    }
    with (run_dir / "summary.json").open("w") as f:
        json.dump(summary, f)

    timeseries = [
        {
            "year": 2025,
            "region": "AUS",
            "commodity": "electricity",
            "price": 50.0,
            "emissions": 500000.0,
        },
        {
            "year": 2026,
            "region": "AUS",
            "commodity": "electricity",
            "price": 48.0,
            "emissions": 450000.0,
        },
        {
            "year": 2027,
            "region": "AUS",
            "commodity": "electricity",
            "price": 45.0,
            "emissions": 400000.0,
        },
    ]
    with (run_dir / "timeseries.json").open("w") as f:
        json.dump(timeseries, f)

    agents = [
        {
            "agent_id": "EGEN1",
            "agent_type": "ElectricityProducer",
            "region": "AUS",
            "initial_capacity": 100.0,
        },
        {
            "agent_id": "EGEN2",
            "agent_type": "ElectricityProducer",
            "region": "AUS",
            "initial_capacity": 150.0,
        },
        {
            "agent_id": "CONS1",
            "agent_type": "Consumer",
            "region": "AUS",
            "initial_capacity": 0.0,
        },
    ]
    with (run_dir / "agents.json").open("w") as f:
        json.dump(agents, f)

    agent_traces = [
        {
            "agent_id": "EGEN1",
            "year": 2025,
            "action": {"invest": {"solar": 10.0}, "retire": {}, "supply": {}},
        },
        {
            "agent_id": "EGEN1",
            "year": 2026,
            "action": {"invest": {"solar": 15.0}, "retire": {}, "supply": {}},
        },
        {
            "agent_id": "EGEN2",
            "year": 2025,
            "action": {"invest": {}, "retire": {"coal": 20.0}, "supply": {}},
        },
        {
            "agent_id": "EGEN2",
            "year": 2026,
            "action": {"invest": {}, "retire": {}, "supply": {"electricity": 100.0}},
        },
    ]
    with (run_dir / "agent_traces.json").open("w") as f:
        json.dump(agent_traces, f)

    with (run_dir / "drivers.json").open("w") as f:
        json.dump([], f)

    return run_dir


@pytest.fixture
def baseline_run_dir(tmp_path: Path) -> Path:
    """Create a baseline run directory for comparison tests."""
    run_dir = tmp_path / "baseline-run"
    run_dir.mkdir()

    manifest = {
        "run_id": "baseline-run",
        "assumptions": {"id": "baseline-v1"},
        "years": {"start": 2025, "end": 2030},
    }
    with (run_dir / "manifest.json").open("w") as f:
        json.dump(manifest, f)

    summary = {
        "run_id": "baseline-run",
        "cumulative_emissions": 1200000.0,
        "peak_emissions": 600000.0,
        "year_net_zero": 2050,
    }
    with (run_dir / "summary.json").open("w") as f:
        json.dump(summary, f)

    return run_dir


class TestGetStoryContext:
    """Tests for get_story_context."""

    def test_returns_context_for_valid_run(self, sample_run_dir: Path) -> None:
        result = get_story_context(sample_run_dir)
        assert result is not None
        assert isinstance(result, StoryContext)
        assert result.run_id == "test-run-123"

    def test_extracts_scenario_name(self, sample_run_dir: Path) -> None:
        result = get_story_context(sample_run_dir)
        assert result is not None
        assert result.scenario_name == "fast-elec-v1"
        assert result.is_scenario_run is True

    def test_extracts_baseline_name(self, sample_run_dir: Path) -> None:
        result = get_story_context(sample_run_dir)
        assert result is not None
        assert result.baseline_name == "baseline-v1"

    def test_extracts_years(self, sample_run_dir: Path) -> None:
        result = get_story_context(sample_run_dir)
        assert result is not None
        assert result.years.start == 2025
        assert result.years.end == 2030

    def test_returns_none_for_missing_manifest(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = get_story_context(empty_dir)
        assert result is None

    def test_handles_yaml_manifest(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "yaml-run"
        run_dir.mkdir()

        manifest = {
            "run_id": "yaml-run",
            "assumptions_manifest": {"id": "baseline-v1"},
            "scenario_manifest": {"id": "scenario-v1"},
        }
        with (run_dir / "manifest.yaml").open("w") as f:
            yaml.safe_dump(manifest, f)

        result = get_story_context(run_dir)
        assert result is not None
        assert result.run_id == "yaml-run"
        assert result.scenario_name == "scenario-v1"

    def test_handles_years_as_list(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "list-years-run"
        run_dir.mkdir()

        manifest = {
            "run_id": "list-years-run",
            "years": [2024, 2025, 2026, 2027],
            "assumptions": {"id": "baseline"},
        }
        with (run_dir / "manifest.json").open("w") as f:
            json.dump(manifest, f)

        result = get_story_context(run_dir)
        assert result is not None
        assert result.years.start == 2024
        assert result.years.end == 2027


class TestGetHeadlineMetrics:
    """Tests for get_headline_metrics."""

    def test_returns_metrics_for_valid_run(self, sample_run_dir: Path) -> None:
        result = get_headline_metrics(sample_run_dir)
        assert result is not None
        assert isinstance(result, HeadlineMetrics)

    def test_extracts_emissions_values(self, sample_run_dir: Path) -> None:
        result = get_headline_metrics(sample_run_dir)
        assert result is not None
        assert result.total_emissions.value == 500000.0
        assert result.cumulative_emissions.value == 1000000.0

    def test_computes_trend_from_timeseries(self, sample_run_dir: Path) -> None:
        result = get_headline_metrics(sample_run_dir)
        assert result is not None
        assert result.total_emissions.trend == "down"

    def test_computes_average_prices(self, sample_run_dir: Path) -> None:
        result = get_headline_metrics(sample_run_dir)
        assert result is not None
        assert len(result.average_price) == 1
        assert result.average_price[0].commodity == "electricity"
        avg_price = (50.0 + 48.0 + 45.0) / 3
        assert abs(result.average_price[0].value - avg_price) < 0.01

    def test_returns_none_for_missing_summary(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = get_headline_metrics(empty_dir)
        assert result is None


class TestGetDrivers:
    """Tests for get_drivers."""

    def test_returns_list_of_drivers(self, sample_run_dir: Path) -> None:
        result = get_drivers(sample_run_dir)
        assert isinstance(result, list)

    def test_drivers_sorted_by_contribution(self, sample_run_dir: Path) -> None:
        result = get_drivers(sample_run_dir)
        if len(result) >= 2:
            contributions = [abs(d.contribution) for d in result]
            assert contributions == sorted(contributions, reverse=True)

    def test_driver_structure(self, sample_run_dir: Path) -> None:
        result = get_drivers(sample_run_dir)
        if result:
            driver = result[0]
            assert isinstance(driver, Driver)
            assert hasattr(driver, "factor")
            assert hasattr(driver, "contribution")
            assert hasattr(driver, "direction")
            assert hasattr(driver, "explanation")
            assert hasattr(driver, "evidence")

    def test_uses_drivers_json_if_exists(self, sample_run_dir: Path) -> None:
        drivers_data = [
            {
                "factor": "Carbon Price",
                "contribution": 0.9,
                "direction": "positive",
                "explanation": "High carbon price drives investment",
                "evidence": ["timeseries: carbon_price"],
            }
        ]
        with (sample_run_dir / "drivers.json").open("w") as f:
            json.dump(drivers_data, f)

        result = get_drivers(sample_run_dir)
        assert len(result) == 1
        assert result[0].factor == "Carbon Price"
        assert result[0].contribution == 0.9

    def test_computes_drivers_from_summary(self, sample_run_dir: Path) -> None:
        result = get_drivers(sample_run_dir)
        factor_names = [d.factor for d in result]
        assert any("Decarbonization" in f or "Scenario" in f for f in factor_names)


class TestGetAgentSummary:
    """Tests for get_agent_summary."""

    def test_returns_summary_for_valid_run(self, sample_run_dir: Path) -> None:
        result = get_agent_summary(sample_run_dir)
        assert result is not None
        assert isinstance(result, AgentSummary)

    def test_counts_agents_by_type(self, sample_run_dir: Path) -> None:
        result = get_agent_summary(sample_run_dir)
        assert result is not None
        assert result.total_agents == 3

        type_counts = {t.type: t.count for t in result.by_type}
        assert type_counts.get("ElectricityProducer", 0) == 2
        assert type_counts.get("Consumer", 0) == 1

    def test_counts_actions(self, sample_run_dir: Path) -> None:
        result = get_agent_summary(sample_run_dir)
        assert result is not None

        producer_summary = next(
            (t for t in result.by_type if t.type == "ElectricityProducer"), None
        )
        assert producer_summary is not None
        assert producer_summary.invest_count == 2
        assert producer_summary.retire_count == 1

    def test_identifies_dominant_behaviour(self, sample_run_dir: Path) -> None:
        result = get_agent_summary(sample_run_dir)
        assert result is not None
        assert result.dominant_behaviour in ["investment", "retirement", "holding"]

    def test_returns_none_for_missing_data(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = get_agent_summary(empty_dir)
        assert result is None


class TestCompareScenarios:
    """Tests for compare_scenarios."""

    def test_returns_none_without_baseline(self, sample_run_dir: Path) -> None:
        result = compare_scenarios(sample_run_dir, None)
        assert result is None

    def test_returns_comparison_with_baseline(
        self, sample_run_dir: Path, baseline_run_dir: Path
    ) -> None:
        result = compare_scenarios(sample_run_dir, baseline_run_dir)
        assert result is not None
        assert isinstance(result, ScenarioComparison)
        assert result.baseline_run_id == "baseline-run"

    def test_computes_key_differences(self, sample_run_dir: Path, baseline_run_dir: Path) -> None:
        result = compare_scenarios(sample_run_dir, baseline_run_dir)
        assert result is not None
        assert len(result.key_differences) > 0

        metric_names = [d.metric for d in result.key_differences]
        assert "Peak Emissions" in metric_names or "Cumulative Emissions" in metric_names

    def test_difference_has_correct_structure(
        self, sample_run_dir: Path, baseline_run_dir: Path
    ) -> None:
        result = compare_scenarios(sample_run_dir, baseline_run_dir)
        assert result is not None

        if result.key_differences:
            diff = result.key_differences[0]
            assert hasattr(diff, "metric")
            assert hasattr(diff, "baseline_value")
            assert hasattr(diff, "scenario_value")
            assert hasattr(diff, "delta")
            assert hasattr(diff, "delta_percent")
            assert hasattr(diff, "interpretation")

    def test_returns_none_for_missing_baseline_summary(
        self, sample_run_dir: Path, tmp_path: Path
    ) -> None:
        empty_baseline = tmp_path / "empty-baseline"
        empty_baseline.mkdir()
        result = compare_scenarios(sample_run_dir, empty_baseline)
        assert result is None


class TestGetCaveats:
    """Tests for get_caveats."""

    def test_returns_caveats_object(self, sample_run_dir: Path) -> None:
        result = get_caveats(sample_run_dir)
        assert isinstance(result, Caveats)

    def test_includes_model_limitations(self, sample_run_dir: Path) -> None:
        result = get_caveats(sample_run_dir)
        assert len(result.model_limitations) > 0
        assert any("projections" in lim.lower() for lim in result.model_limitations)

    def test_includes_interpretation_guidance(self, sample_run_dir: Path) -> None:
        result = get_caveats(sample_run_dir)
        assert len(result.interpretation_guidance) > 0

    def test_includes_scenario_specific_from_manifest(self, sample_run_dir: Path) -> None:
        result = get_caveats(sample_run_dir)
        assert len(result.scenario_specific) > 0
        assert any("electrification" in c.lower() for c in result.scenario_specific)

    def test_works_without_manifest(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = get_caveats(empty_dir)
        assert isinstance(result, Caveats)
        assert len(result.model_limitations) > 0


class TestExplainAgentBehaviour:
    """Tests for explain_agent_behaviour."""

    def test_returns_dict(self, sample_run_dir: Path) -> None:
        result = explain_agent_behaviour(sample_run_dir, "ElectricityProducer")
        assert isinstance(result, dict)

    def test_finds_matching_agents(self, sample_run_dir: Path) -> None:
        result = explain_agent_behaviour(sample_run_dir, "ElectricityProducer")
        assert result["found"] is True
        assert result["agent_count"] == 2

    def test_counts_decisions(self, sample_run_dir: Path) -> None:
        result = explain_agent_behaviour(sample_run_dir, "ElectricityProducer")
        assert result["invest_count"] == 2
        assert result["retire_count"] == 1
        assert result["hold_count"] == 1

    def test_identifies_dominant_pattern(self, sample_run_dir: Path) -> None:
        result = explain_agent_behaviour(sample_run_dir, "ElectricityProducer")
        assert "dominant_pattern" in result
        assert result["dominant_pattern"] in ["investment-focused", "retirement-focused", "holding"]

    def test_handles_missing_agent_type(self, sample_run_dir: Path) -> None:
        result = explain_agent_behaviour(sample_run_dir, "NonexistentType")
        assert result["found"] is False
        assert "message" in result

    def test_case_insensitive_matching(self, sample_run_dir: Path) -> None:
        result = explain_agent_behaviour(sample_run_dir, "electricityproducer")
        assert result["found"] is True


class TestToDict:
    """Tests for to_dict helper."""

    def test_converts_dataclass(self, sample_run_dir: Path) -> None:
        context = get_story_context(sample_run_dir)
        result = to_dict(context)
        assert isinstance(result, dict)
        assert result["run_id"] == "test-run-123"

    def test_converts_list_of_dataclasses(self, sample_run_dir: Path) -> None:
        drivers = get_drivers(sample_run_dir)
        result = to_dict(drivers)
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], dict)

    def test_handles_none(self) -> None:
        result = to_dict(None)
        assert result is None

    def test_passes_through_non_dataclass(self) -> None:
        result = to_dict({"key": "value"})
        assert result == {"key": "value"}


class TestToolDefinitions:
    """Tests for tool_definitions module."""

    def test_get_tool_definitions_returns_list(self) -> None:
        tools = get_tool_definitions()
        assert isinstance(tools, list)
        assert len(tools) == 7

    def test_all_tools_have_required_fields(self) -> None:
        tools = get_tool_definitions()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"

    def test_get_tool_by_name_found(self) -> None:
        tool = get_tool_by_name("get_story_context")
        assert tool is not None
        assert tool["name"] == "get_story_context"

    def test_get_tool_by_name_not_found(self) -> None:
        tool = get_tool_by_name("nonexistent_tool")
        assert tool is None

    def test_tool_names_match_functions(self) -> None:
        expected_names = {
            "get_story_context",
            "get_headline_metrics",
            "get_drivers",
            "get_agent_summary",
            "compare_scenarios",
            "get_caveats",
            "explain_agent_behaviour",
        }
        tools = get_tool_definitions()
        actual_names = {t["name"] for t in tools}
        assert actual_names == expected_names
