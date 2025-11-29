"""Dataclasses defining the world, agent and action structures.

These lightweight containers hold the state of the world, the private
state of each agent, and the actions chosen by agents each timestep.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
import pandas as pd


@dataclass(frozen=True)
class WorldState:
    """Shared world state visible to all agents and the simulation engine."""

    t: int
    prices: Dict[str, float]
    demand: Dict[str, float]
    policy: pd.DataFrame
    assumptions: pd.DataFrame
    flows: Dict[str, float] = field(default_factory=dict)
    emissions: float = 0.0


@dataclass
class AgentState:
    """Private state for an individual agent."""

    id: str
    agent_type: str
    region: str
    sector: Optional[str] = None
    tech: Optional[str] = None
    capacity: float = 0.0
    vintage: int = 0
    cash: float = 0.0
    horizon: int = 1
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """Action chosen by an agent at a timestep."""

    agent_id: str
    supply: Dict[str, float]
    invest: Dict[str, float]
    retire: Dict[str, float]
    emissions: float