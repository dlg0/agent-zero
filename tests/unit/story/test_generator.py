"""Unit tests for agent_zero.story.generator module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_zero.story.generator import (
    StoryGenerator,
    StoryOutput,
    StoryProvenance,
    ToolCall,
    _build_system_prompt,
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
    ]
    with (run_dir / "agents.json").open("w") as f:
        json.dump(agents, f)

    agent_traces = [
        {
            "agent_id": "EGEN1",
            "year": 2025,
            "action": {"invest": {"solar": 10.0}, "retire": {}, "supply": {}},
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


class TestStoryGenerator:
    """Tests for StoryGenerator class."""

    def test_init_validates_run_dir_exists(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="does not exist"):
            StoryGenerator(run_dir=nonexistent)

    def test_init_with_valid_run_dir(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        assert generator.run_dir == sample_run_dir
        assert generator.audience == "generalist"

    def test_init_with_custom_audience(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, audience="technical")
        assert generator.audience == "technical"

    def test_init_with_baseline_dir(self, sample_run_dir: Path, baseline_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, baseline_dir=baseline_run_dir)
        assert generator.baseline_dir == baseline_run_dir


class TestBuildSystemPrompt:
    """Tests for _build_system_prompt function."""

    def test_includes_audience_description(self) -> None:
        prompt = _build_system_prompt("generalist")
        assert "general audience" in prompt

    def test_technical_audience_prompt(self) -> None:
        prompt = _build_system_prompt("technical")
        assert "technical audience" in prompt

    def test_expert_audience_prompt(self) -> None:
        prompt = _build_system_prompt("expert")
        assert "expert analysts" in prompt

    def test_includes_story_structure(self) -> None:
        prompt = _build_system_prompt("generalist")
        assert "Executive Summary" in prompt
        assert "Key Findings" in prompt
        assert "What Drives Results" in prompt
        assert "How Agents Behave" in prompt
        assert "Caveats & Limitations" in prompt

    def test_includes_formatting_guidelines(self) -> None:
        prompt = _build_system_prompt("generalist")
        assert "markdown" in prompt.lower()


class TestExecuteTool:
    """Tests for tool execution."""

    def test_execute_get_story_context(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool(
            "get_story_context", {"run_dir": str(sample_run_dir)}
        )
        assert result is not None
        assert "test-run-123" in summary

    def test_execute_get_headline_metrics(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool(
            "get_headline_metrics", {"run_dir": str(sample_run_dir)}
        )
        assert result is not None
        assert "Emissions" in summary

    def test_execute_get_drivers(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool("get_drivers", {"run_dir": str(sample_run_dir)})
        assert isinstance(result, list)
        assert "drivers found" in summary

    def test_execute_get_agent_summary(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool(
            "get_agent_summary", {"run_dir": str(sample_run_dir)}
        )
        assert result is not None
        assert "agents" in summary.lower()

    def test_execute_get_caveats(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool("get_caveats", {"run_dir": str(sample_run_dir)})
        assert result is not None
        assert "limitations" in summary

    def test_execute_compare_scenarios_without_baseline(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool(
            "compare_scenarios", {"run_dir": str(sample_run_dir)}
        )
        assert result is None
        assert "No comparison" in summary

    def test_execute_compare_scenarios_with_baseline(
        self, sample_run_dir: Path, baseline_run_dir: Path
    ) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, baseline_dir=baseline_run_dir)
        result, summary = generator._execute_tool(
            "compare_scenarios", {"run_dir": str(sample_run_dir)}
        )
        assert result is not None
        assert "differences" in summary

    def test_execute_explain_agent_behaviour(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool(
            "explain_agent_behaviour",
            {"run_dir": str(sample_run_dir), "agent_type": "ElectricityProducer"},
        )
        assert result["found"] is True
        assert "pattern" in summary.lower()

    def test_execute_unknown_tool(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result, summary = generator._execute_tool("unknown_tool", {"run_dir": str(sample_run_dir)})
        assert "error" in result
        assert summary == "Unknown tool"


class TestGenerateOffline:
    """Tests for generate_offline method."""

    def test_returns_story_output(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result = generator.generate_offline()
        assert isinstance(result, StoryOutput)
        assert isinstance(result.story_markdown, str)
        assert isinstance(result.provenance, StoryProvenance)

    def test_includes_automatically_generated_note(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result = generator.generate_offline()
        assert "automatically generated" in result.story_markdown.lower()

    def test_includes_all_sections(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result = generator.generate_offline()

        assert "## Executive Summary" in result.story_markdown
        assert "## Key Findings" in result.story_markdown
        assert "## What Drives Results" in result.story_markdown
        assert "## How Agents Behave" in result.story_markdown
        assert "## Caveats & Limitations" in result.story_markdown

    def test_includes_metrics_data(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result = generator.generate_offline()

        assert "emissions" in result.story_markdown.lower()
        assert "MtCO2e" in result.story_markdown

    def test_provenance_has_correct_model(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result = generator.generate_offline()

        assert result.provenance.model == "offline-template"
        assert result.provenance.model_version == "1.0.0"

    def test_provenance_tracks_tools_called(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)
        result = generator.generate_offline()

        tool_names = [tc.tool_name for tc in result.provenance.tools_called]
        assert "get_story_context" in tool_names
        assert "get_headline_metrics" in tool_names
        assert "get_drivers" in tool_names
        assert "get_caveats" in tool_names

    def test_includes_scenario_comparison_when_available(
        self, sample_run_dir: Path, baseline_run_dir: Path
    ) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, baseline_dir=baseline_run_dir)
        result = generator.generate_offline()

        assert "## Scenario Impact" in result.story_markdown
        assert "baseline" in result.story_markdown.lower()


class TestGenerateWithMockedClient:
    """Tests for generate method with mocked Anthropic client."""

    def _create_mock_response(
        self,
        content: list[Any],
        stop_reason: str = "end_turn",
        model: str = "claude-sonnet-4-20250514",
    ) -> MagicMock:
        """Create a mock Anthropic response."""
        response = MagicMock()
        response.content = content
        response.stop_reason = stop_reason
        response.model = model
        return response

    def _create_text_block(self, text: str) -> MagicMock:
        """Create a mock text content block."""
        block = MagicMock()
        block.type = "text"
        block.text = text
        return block

    def _create_tool_use_block(
        self, tool_id: str, name: str, input_data: dict[str, Any]
    ) -> MagicMock:
        """Create a mock tool use content block."""
        block = MagicMock()
        block.type = "tool_use"
        block.id = tool_id
        block.name = name
        block.input = input_data
        return block

    def _patch_anthropic(self) -> Any:
        """Create a patch for the anthropic module import."""
        import sys

        mock_anthropic_module = MagicMock()
        return patch.dict(sys.modules, {"anthropic": mock_anthropic_module})

    def test_generate_requires_api_key(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir)

        mock_anthropic_module = MagicMock()
        with (
            patch.dict("sys.modules", {"anthropic": mock_anthropic_module}),
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="API key is required"),
        ):
            generator.generate()

    def test_generate_uses_provided_api_key(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, api_key="test-key")

        final_response = self._create_mock_response(
            [self._create_text_block("# Generated Story\n\nThis is a test story.")]
        )

        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = final_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = generator.generate()

            mock_anthropic_module.Anthropic.assert_called_once_with(api_key="test-key")
            assert isinstance(result, StoryOutput)

    def test_generate_returns_story_from_final_response(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, api_key="test-key")

        expected_story = "# Test Story\n\nThis is the generated narrative."
        final_response = self._create_mock_response([self._create_text_block(expected_story)])

        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = final_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = generator.generate()

            assert result.story_markdown == expected_story

    def test_generate_handles_tool_use_loop(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, api_key="test-key")

        tool_response = self._create_mock_response(
            [
                self._create_tool_use_block(
                    "tool-1", "get_story_context", {"run_dir": str(sample_run_dir)}
                )
            ],
            stop_reason="tool_use",
        )

        final_response = self._create_mock_response([self._create_text_block("# Final Story")])

        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [tool_response, final_response]
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = generator.generate()

            assert mock_client.messages.create.call_count == 2
            assert len(result.provenance.tools_called) == 1
            assert result.provenance.tools_called[0].tool_name == "get_story_context"

    def test_generate_tracks_multiple_tool_calls(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, api_key="test-key")

        tool_response1 = self._create_mock_response(
            [
                self._create_tool_use_block(
                    "tool-1", "get_story_context", {"run_dir": str(sample_run_dir)}
                ),
                self._create_tool_use_block(
                    "tool-2", "get_headline_metrics", {"run_dir": str(sample_run_dir)}
                ),
            ],
            stop_reason="tool_use",
        )

        final_response = self._create_mock_response(
            [self._create_text_block("# Story with multiple tools")]
        )

        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [tool_response1, final_response]
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = generator.generate()

            assert len(result.provenance.tools_called) == 2
            tool_names = [tc.tool_name for tc in result.provenance.tools_called]
            assert "get_story_context" in tool_names
            assert "get_headline_metrics" in tool_names

    def test_generate_records_provenance(self, sample_run_dir: Path) -> None:
        generator = StoryGenerator(run_dir=sample_run_dir, api_key="test-key", audience="technical")

        final_response = self._create_mock_response(
            [self._create_text_block("# Story")], model="claude-sonnet-4-20250514"
        )

        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = final_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = generator.generate()

            assert result.provenance.run_id == "test-run-123"
            assert result.provenance.audience == "technical"
            assert result.provenance.model == "claude-sonnet-4-20250514"
            assert result.provenance.generated_at is not None
            assert result.provenance.generation_time_seconds >= 0


class TestToolCallDataclass:
    """Tests for ToolCall dataclass."""

    def test_tool_call_creation(self) -> None:
        tc = ToolCall(
            tool_name="get_story_context",
            arguments={"run_dir": "/path/to/run"},
            result_summary="Context loaded",
        )
        assert tc.tool_name == "get_story_context"
        assert tc.arguments == {"run_dir": "/path/to/run"}
        assert tc.result_summary == "Context loaded"


class TestStoryProvenanceDataclass:
    """Tests for StoryProvenance dataclass."""

    def test_provenance_creation(self) -> None:
        prov = StoryProvenance(
            run_id="test-123",
            audience="generalist",
            generated_at="2024-01-01T00:00:00Z",
            model="claude-sonnet-4-20250514",
            model_version="claude-sonnet-4-20250514",
            tools_called=[],
            generation_time_seconds=1.5,
        )
        assert prov.run_id == "test-123"
        assert prov.audience == "generalist"
        assert prov.generation_time_seconds == 1.5


class TestStoryOutputDataclass:
    """Tests for StoryOutput dataclass."""

    def test_story_output_creation(self) -> None:
        prov = StoryProvenance(
            run_id="test-123",
            audience="generalist",
            generated_at="2024-01-01T00:00:00Z",
            model="offline-template",
            model_version="1.0.0",
            tools_called=[],
            generation_time_seconds=0.1,
        )
        output = StoryOutput(story_markdown="# Test", provenance=prov)
        assert output.story_markdown == "# Test"
        assert output.provenance.run_id == "test-123"
