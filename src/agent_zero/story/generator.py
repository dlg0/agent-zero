"""Story generator using Claude with tool calling.

This module provides an agentic story generator that uses Claude to
generate narrative content about simulation runs by calling data tools.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from agent_zero.story.tool_definitions import get_tool_definitions
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


@dataclass
class ToolCall:
    """Record of a tool call made during generation."""

    tool_name: str
    arguments: dict[str, Any]
    result_summary: str


@dataclass
class StoryProvenance:
    """Provenance information for a generated story."""

    run_id: str
    audience: str
    generated_at: str
    model: str
    model_version: str
    tools_called: list[ToolCall]
    generation_time_seconds: float


@dataclass
class StoryOutput:
    """Output from story generation."""

    story_markdown: str
    provenance: StoryProvenance


AUDIENCE_DESCRIPTIONS = {
    "generalist": (
        "a general audience without technical background. "
        "Use plain language, avoid jargon, and explain concepts simply. "
        "Focus on the big picture and key takeaways."
    ),
    "technical": (
        "a technical audience familiar with energy systems and modeling. "
        "Use appropriate technical terminology but still explain specialized concepts. "
        "Include quantitative details and methodology notes."
    ),
    "expert": (
        "expert analysts and modelers who understand agent-based modeling deeply. "
        "Be precise with terminology, include detailed metrics, and discuss "
        "modeling assumptions and limitations explicitly."
    ),
}


def _build_system_prompt(audience: Literal["generalist", "technical", "expert"]) -> str:
    """Build the system prompt for Claude based on audience level."""
    audience_desc = AUDIENCE_DESCRIPTIONS.get(audience, AUDIENCE_DESCRIPTIONS["generalist"])

    return f"""You are an AgentZero story generator. Your role is to create clear, accurate,
and compelling narratives about energy system simulation results.

## Audience
You are writing for {audience_desc}

## Story Structure
Generate a markdown story with the following sections:

### Executive Summary
Write a single paragraph (3-5 sentences) that captures the most important findings.
Lead with the key insight.

### Key Findings
Present 3-5 bullet points with specific numbers from the data:
- Each bullet should have a concrete metric or percentage
- Order by importance/impact
- Use the actual values from the tools

### What Drives Results
Write 2-3 paragraphs explaining the main factors that drive the outcomes:
- Reference the drivers data
- Explain cause and effect relationships
- Connect assumptions to outcomes

### How Agents Behave
Summarize agent decision patterns:
- What types of agents are present
- What is the dominant behaviour (investment, retirement, holding)
- Any notable patterns by agent type

### Scenario Impact
(Include this section only for scenario runs)
Compare against baseline:
- Key differences in metrics
- What assumptions changed
- Interpretation of the impact

### Caveats & Limitations
This section is MANDATORY. Include:
- Model limitations
- Data limitations if any
- Interpretation guidance
- Any scenario-specific caveats

## Formatting Guidelines
- Use markdown formatting throughout
- Include inline citations like [source: metric_name] when referencing data
- Use tables for comparative data when helpful
- Bold key numbers and findings
- Keep paragraphs focused and concise

## Tool Usage
Use the available tools to gather data for your story:
1. Start with get_story_context to understand the run
2. Get headline_metrics for key numbers
3. Get drivers to understand what's causing outcomes
4. Get agent_summary for behaviour patterns
5. If this is a scenario run, use compare_scenarios
6. Always call get_caveats for the limitations section

Be thorough - call all relevant tools before writing the story."""


@dataclass
class StoryGenerator:
    """Generator for narrative stories about simulation runs.

    Uses Claude with tool calling to gather data and generate
    a structured narrative about simulation results.
    """

    run_dir: Path
    audience: Literal["generalist", "technical", "expert"] = "generalist"
    baseline_dir: Path | None = None
    api_key: str | None = None
    _client: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.run_dir.exists():
            raise ValueError(f"Run directory does not exist: {self.run_dir}")

    def _get_client(self) -> Any:
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic  # type: ignore[import-not-found]
            except ImportError as e:
                raise ImportError(
                    "anthropic package is required for story generation. "
                    "Install it with: pip install 'agent-zero[story]'"
                ) from e

            api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "Anthropic API key is required. "
                    "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
                )

            self._client = Anthropic(api_key=api_key)

        return self._client

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> tuple[Any, str]:
        """Execute a tool and return the result with a summary.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Tuple of (result, summary_string)
        """
        run_dir = Path(arguments.get("run_dir", str(self.run_dir)))

        if tool_name == "get_story_context":
            ctx_result = get_story_context(run_dir)
            summary = f"Context for run {ctx_result.run_id}" if ctx_result else "No context found"
            return ctx_result, summary

        if tool_name == "get_headline_metrics":
            metrics_result = get_headline_metrics(run_dir)
            if metrics_result:
                summary = (
                    f"Emissions: {metrics_result.total_emissions.value} "
                    f"{metrics_result.total_emissions.unit}, "
                    f"trend: {metrics_result.total_emissions.trend}"
                )
            else:
                summary = "No metrics found"
            return metrics_result, summary

        if tool_name == "get_drivers":
            drivers_result = get_drivers(run_dir)
            summary = (
                f"{len(drivers_result)} drivers found" if drivers_result else "No drivers found"
            )
            return drivers_result, summary

        if tool_name == "get_agent_summary":
            agents_result = get_agent_summary(run_dir)
            if agents_result:
                summary = (
                    f"{agents_result.total_agents} agents, "
                    f"dominant behaviour: {agents_result.dominant_behaviour}"
                )
            else:
                summary = "No agent data found"
            return agents_result, summary

        if tool_name == "compare_scenarios":
            baseline_dir_arg = arguments.get("baseline_dir")
            baseline = Path(baseline_dir_arg) if baseline_dir_arg else self.baseline_dir
            comparison_result = compare_scenarios(run_dir, baseline)
            if comparison_result:
                summary = f"{len(comparison_result.key_differences)} key differences from baseline"
            else:
                summary = "No comparison available"
            return comparison_result, summary

        if tool_name == "get_caveats":
            caveats_result = get_caveats(run_dir)
            summary = f"{len(caveats_result.model_limitations)} model limitations"
            return caveats_result, summary

        if tool_name == "explain_agent_behaviour":
            agent_type = arguments.get("agent_type", "")
            explain_result = explain_agent_behaviour(run_dir, agent_type)
            if explain_result.get("found"):
                summary = (
                    f"{agent_type}: {explain_result.get('dominant_pattern', 'unknown')} pattern"
                )
            else:
                summary = f"No agents of type {agent_type} found"
            return explain_result, summary

        return {"error": f"Unknown tool: {tool_name}"}, "Unknown tool"

    def generate(self) -> StoryOutput:
        """Generate the story using Claude with tool calling.

        Returns:
            StoryOutput containing the generated markdown and provenance
        """
        start_time = time.time()
        client = self._get_client()

        system_prompt = _build_system_prompt(self.audience)
        tools = get_tool_definitions()

        for tool in tools:
            if "run_dir" in tool["input_schema"].get("properties", {}):
                tool["input_schema"]["properties"]["run_dir"]["default"] = str(self.run_dir)

        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    f"Generate a story about the simulation run at {self.run_dir}. "
                    f"Use the tools to gather data and then write a comprehensive narrative."
                ),
            }
        ]

        tools_called: list[ToolCall] = []
        model = "claude-sonnet-4-20250514"
        model_version = model

        while True:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )

            model_version = response.model if hasattr(response, "model") else model

            if response.stop_reason == "end_turn":
                story_markdown = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        story_markdown = block.text
                        break
                break

            if response.stop_reason == "tool_use":
                assistant_message = {"role": "assistant", "content": response.content}
                messages.append(assistant_message)

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input if isinstance(block.input, dict) else {}

                        if "run_dir" not in tool_input:
                            tool_input["run_dir"] = str(self.run_dir)

                        result, summary = self._execute_tool(tool_name, tool_input)
                        result_json = json.dumps(to_dict(result))

                        tools_called.append(
                            ToolCall(
                                tool_name=tool_name,
                                arguments=tool_input,
                                result_summary=summary,
                            )
                        )

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_json,
                            }
                        )

                messages.append({"role": "user", "content": tool_results})
            else:
                story_markdown = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        story_markdown = block.text
                        break
                break

        generation_time = time.time() - start_time

        context = get_story_context(self.run_dir)
        run_id = context.run_id if context else self.run_dir.name

        provenance = StoryProvenance(
            run_id=run_id,
            audience=self.audience,
            generated_at=datetime.now(UTC).isoformat(),
            model=model,
            model_version=model_version,
            tools_called=tools_called,
            generation_time_seconds=round(generation_time, 2),
        )

        return StoryOutput(story_markdown=story_markdown, provenance=provenance)

    def generate_offline(self) -> StoryOutput:
        """Generate story without LLM using templates (fallback).

        This method provides a basic story structure by calling tools
        directly and formatting results into a template. Useful when
        LLM access is not available.

        Returns:
            StoryOutput containing the template-generated markdown and provenance
        """
        start_time = time.time()
        tools_called: list[ToolCall] = []

        context = get_story_context(self.run_dir)
        tools_called.append(
            ToolCall(
                tool_name="get_story_context",
                arguments={"run_dir": str(self.run_dir)},
                result_summary=f"Context for run {context.run_id}" if context else "No context",
            )
        )

        metrics = get_headline_metrics(self.run_dir)
        tools_called.append(
            ToolCall(
                tool_name="get_headline_metrics",
                arguments={"run_dir": str(self.run_dir)},
                result_summary="Metrics loaded" if metrics else "No metrics",
            )
        )

        drivers = get_drivers(self.run_dir)
        tools_called.append(
            ToolCall(
                tool_name="get_drivers",
                arguments={"run_dir": str(self.run_dir)},
                result_summary=f"{len(drivers)} drivers found",
            )
        )

        agents = get_agent_summary(self.run_dir)
        tools_called.append(
            ToolCall(
                tool_name="get_agent_summary",
                arguments={"run_dir": str(self.run_dir)},
                result_summary=f"{agents.total_agents} agents" if agents else "No agents",
            )
        )

        comparison = None
        if context and context.is_scenario_run and self.baseline_dir:
            comparison = compare_scenarios(self.run_dir, self.baseline_dir)
            tools_called.append(
                ToolCall(
                    tool_name="compare_scenarios",
                    arguments={
                        "run_dir": str(self.run_dir),
                        "baseline_dir": str(self.baseline_dir),
                    },
                    result_summary=(
                        f"{len(comparison.key_differences)} differences"
                        if comparison
                        else "No comparison"
                    ),
                )
            )

        caveats = get_caveats(self.run_dir)
        tools_called.append(
            ToolCall(
                tool_name="get_caveats",
                arguments={"run_dir": str(self.run_dir)},
                result_summary=f"{len(caveats.model_limitations)} limitations",
            )
        )

        story_parts = [
            "# Simulation Results Summary",
            "",
            "*This story was automatically generated without LLM processing.*",
            "",
        ]

        story_parts.append("## Executive Summary")
        story_parts.append("")
        if context:
            story_parts.append(
                f"This report summarizes results from simulation run **{context.run_id}** "
                f"covering the period {context.years.start}-{context.years.end}."
            )
            if context.is_scenario_run and context.scenario_name:
                story_parts.append(
                    f" This is a scenario run (**{context.scenario_name}**) "
                    f"compared against baseline {context.baseline_name}."
                )
        else:
            story_parts.append(
                f"This report summarizes results from the simulation run at {self.run_dir}."
            )
        story_parts.append("")

        story_parts.append("## Key Findings")
        story_parts.append("")
        if metrics:
            story_parts.append(
                f"- **Total emissions**: {metrics.total_emissions.value:.1f} "
                f"{metrics.total_emissions.unit} (trend: {metrics.total_emissions.trend}) "
                "[source: total_emissions]"
            )
            story_parts.append(
                f"- **Cumulative emissions**: {metrics.cumulative_emissions.value:.1f} "
                f"{metrics.cumulative_emissions.unit} [source: cumulative_emissions]"
            )
            story_parts.append(
                f"- **Peak capacity**: {metrics.peak_capacity.value:.1f} "
                f"{metrics.peak_capacity.unit} in {metrics.peak_capacity.year} "
                "[source: peak_capacity]"
            )
            story_parts.append(
                f"- **Total investment**: ${metrics.total_investment.value:,.0f} "
                "[source: total_investment]"
            )
        else:
            story_parts.append("- No headline metrics available")
        story_parts.append("")

        story_parts.append("## What Drives Results")
        story_parts.append("")
        if drivers:
            for driver in drivers[:3]:
                direction = "↑" if driver.direction == "positive" else "↓"
                story_parts.append(
                    f"**{driver.factor}** ({direction} {driver.contribution:.0%}): "
                    f"{driver.explanation} [source: {', '.join(driver.evidence)}]"
                )
                story_parts.append("")
        else:
            story_parts.append("No driver analysis available.")
        story_parts.append("")

        story_parts.append("## How Agents Behave")
        story_parts.append("")
        if agents:
            story_parts.append(
                f"The simulation includes **{agents.total_agents} agents** "
                f"with dominant behaviour: **{agents.dominant_behaviour}**."
            )
            story_parts.append("")
            if agents.by_type:
                story_parts.append("| Agent Type | Count | Invest | Retire | Hold |")
                story_parts.append("|------------|-------|--------|--------|------|")
                for at in agents.by_type:
                    story_parts.append(
                        f"| {at.type} | {at.count} | {at.invest_count} | "
                        f"{at.retire_count} | {at.hold_count} |"
                    )
            story_parts.append("")
            if agents.notable_patterns:
                story_parts.append("Notable patterns:")
                for pattern in agents.notable_patterns:
                    story_parts.append(f"- {pattern}")
        else:
            story_parts.append("No agent data available.")
        story_parts.append("")

        if comparison:
            story_parts.append("## Scenario Impact")
            story_parts.append("")
            story_parts.append(f"Compared to baseline **{comparison.baseline_run_id}**:")
            story_parts.append("")
            if comparison.key_differences:
                for diff in comparison.key_differences:
                    story_parts.append(f"- {diff.interpretation}")
            if comparison.assumption_changes:
                story_parts.append("")
                story_parts.append("Assumption changes:")
                for change in comparison.assumption_changes:
                    story_parts.append(
                        f"- **{change.param}**: {change.baseline} → {change.scenario}"
                    )
            story_parts.append("")

        story_parts.append("## Caveats & Limitations")
        story_parts.append("")
        story_parts.append("### Model Limitations")
        for limitation in caveats.model_limitations:
            story_parts.append(f"- {limitation}")
        story_parts.append("")
        if caveats.scenario_specific:
            story_parts.append("### Scenario-Specific Notes")
            for note in caveats.scenario_specific:
                story_parts.append(f"- {note}")
            story_parts.append("")
        story_parts.append("### Interpretation Guidance")
        for guidance in caveats.interpretation_guidance:
            story_parts.append(f"- {guidance}")

        story_markdown = "\n".join(story_parts)
        generation_time = time.time() - start_time

        run_id = context.run_id if context else self.run_dir.name

        provenance = StoryProvenance(
            run_id=run_id,
            audience=self.audience,
            generated_at=datetime.now(UTC).isoformat(),
            model="offline-template",
            model_version="1.0.0",
            tools_called=tools_called,
            generation_time_seconds=round(generation_time, 2),
        )

        return StoryOutput(story_markdown=story_markdown, provenance=provenance)
