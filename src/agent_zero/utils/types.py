"""Dataclasses defining the world, agent and action structures.

These lightweight containers hold the state of the world, the private
state of each agent, and the actions chosen by agents each timestep.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class WorldState:
    """Shared world state visible to all agents and the simulation engine."""

    t: int
    prices: dict[str, float]
    demand: dict[str, float]
    policy: pd.DataFrame
    assumptions: pd.DataFrame
    flows: dict[str, float] = field(default_factory=dict)
    emissions: float = 0.0


@dataclass
class AgentState:
    """Private state for an individual agent."""

    id: str
    agent_type: str
    region: str
    sector: str | None = None
    tech: str | None = None
    capacity: float = 0.0
    vintage: int = 0
    cash: float = 0.0
    horizon: int = 1
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """Action chosen by an agent at a timestep."""

    agent_id: str
    supply: dict[str, float]
    invest: dict[str, float]
    retire: dict[str, float]
    emissions: float
    expected_price: float | None = None
    action_inputs: dict[str, Any] | None = None
    state_before: dict[str, Any] | None = None
    state_after: dict[str, Any] | None = None
