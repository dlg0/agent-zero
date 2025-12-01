"""Tool definitions for LLM/MCP integration.

This module provides tool schemas in a format suitable for Claude/MCP,
matching the Anthropic tool use specification.
"""

from __future__ import annotations

from typing import Any

STORY_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_story_context",
        "description": (
            "Load run manifest and return story context including run ID, "
            "scenario name, baseline name, simulation years, and whether "
            "this is a scenario run. Use this first to understand the run."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the run directory containing manifest.json or manifest.yaml",
                }
            },
            "required": ["run_dir"],
        },
    },
    {
        "name": "get_headline_metrics",
        "description": (
            "Load summary and timeseries data to compute headline metrics "
            "including total emissions, cumulative emissions, peak capacity, "
            "total investment, and average prices. Returns key numbers for "
            "building the story narrative."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the run directory",
                }
            },
            "required": ["run_dir"],
        },
    },
    {
        "name": "get_drivers",
        "description": (
            "Load or compute the key drivers of simulation results. "
            "Returns factors ranked by their contribution to outcomes, "
            "including direction (positive/negative) and supporting evidence."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the run directory",
                }
            },
            "required": ["run_dir"],
        },
    },
    {
        "name": "get_agent_summary",
        "description": (
            "Load agent data and compute aggregated behaviour summary. "
            "Returns counts by agent type, invest/retire/hold actions, "
            "dominant behaviour patterns, and notable observations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the run directory",
                }
            },
            "required": ["run_dir"],
        },
    },
    {
        "name": "compare_scenarios",
        "description": (
            "Compare a scenario run against a baseline run. "
            "Computes deltas for key metrics like peak emissions, "
            "cumulative emissions, and year of net zero. "
            "Also extracts assumption changes between runs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the scenario run directory",
                },
                "baseline_dir": {
                    "type": "string",
                    "description": "Path to the baseline run directory for comparison",
                },
            },
            "required": ["run_dir"],
        },
    },
    {
        "name": "get_caveats",
        "description": (
            "Return model limitations and scenario-specific caveats. "
            "Includes standard model limitations, data limitations, "
            "scenario-specific notes, and interpretation guidance. "
            "Use this to ensure responsible communication of results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the run directory",
                }
            },
            "required": ["run_dir"],
        },
    },
    {
        "name": "explain_agent_behaviour",
        "description": (
            "Filter agent traces to a specific agent type and summarize "
            "their decision patterns. Returns investment/retirement counts, "
            "dominant behaviour, and year-by-year decision breakdown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the run directory",
                },
                "agent_type": {
                    "type": "string",
                    "description": "The agent type to filter and explain (e.g., 'ElectricityProducer')",
                },
            },
            "required": ["run_dir", "agent_type"],
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return all story tool definitions for LLM/MCP registration.

    Returns:
        List of tool definition dictionaries in Anthropic tool format
    """
    return STORY_TOOLS


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a specific tool definition by name.

    Args:
        name: The tool name to look up

    Returns:
        Tool definition dictionary or None if not found
    """
    for tool in STORY_TOOLS:
        if tool["name"] == name:
            return tool
    return None
