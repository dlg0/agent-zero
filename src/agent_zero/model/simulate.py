"""Run the toy simulation through a sequence of years.

At each time step agents observe the world, decide on actions and
markets are cleared. New world and agent states are returned along
with the actions taken. A full run accumulates these tuples in
a history list.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..utils.types import Action, AgentState, WorldState
from .decisions import decide
from .markets import clear_markets


def _agent_to_dict(agent: AgentState) -> dict[str, Any]:
    """Convert an AgentState to a dict for state capture."""
    return {
        "id": agent.id,
        "agent_type": agent.agent_type,
        "region": agent.region,
        "sector": agent.sector,
        "tech": agent.tech,
        "capacity": agent.capacity,
        "vintage": agent.vintage,
        "cash": agent.cash,
        "horizon": agent.horizon,
        "params": dict(agent.params) if agent.params else {},
    }


def step(
    world: WorldState, agents: list[AgentState]
) -> tuple[WorldState, list[AgentState], list[Action]]:
    """Perform one simulation step.

    1. Each agent decides on an action given the current world state.
    2. Market clearing updates prices and aggregates flows and emissions.
    3. Agent capacities are updated according to their investment actions.
    4. Demand for the next year is updated from assumptions, if available.
    5. The time is advanced by one year.
    """
    # Capture state_before for each agent
    states_before: dict[str, dict[str, Any]] = {ag.id: _agent_to_dict(ag) for ag in agents}

    # 1. Agent decisions
    actions: list[Action] = [decide(a, world) for a in agents]

    # 2. Market clearing
    world2 = clear_markets(world, actions)

    # 3. Update agent capacities with their investments
    updated_agents: list[AgentState] = []
    for ag in agents:
        act = next((x for x in actions if x.agent_id == ag.id), None)
        if act and ag.agent_type in ("ElectricityProducer", "HydrogenProducer"):
            tech = ag.tech or ""
            ag.capacity += act.invest.get(tech, 0.0)
        updated_agents.append(ag)

    # Capture state_after and attach to actions
    actions_with_traces: list[Action] = []
    for act in actions:
        state_before = states_before.get(act.agent_id)
        agent_after = next((a for a in updated_agents if a.id == act.agent_id), None)
        state_after = _agent_to_dict(agent_after) if agent_after else None
        actions_with_traces.append(replace(act, state_before=state_before, state_after=state_after))

    # 4. Update demand for next year from assumptions, if specified
    t_next = world2.t + 1
    demand = dict(world2.demand)
    for commodity in ["electricity", "hydrogen"]:
        mask = (
            (world2.assumptions["year"] == t_next)
            & (world2.assumptions["param"] == "demand")
            & (world2.assumptions["tech"] == commodity)
        )
        if mask.any():
            demand[commodity] = float(world2.assumptions.loc[mask, "value"].iloc[0])

    # 5. Advance time
    world3 = WorldState(
        t=world2.t + 1,
        prices=world2.prices,
        demand=demand,
        policy=world2.policy,
        assumptions=world2.assumptions,
        flows=world2.flows,
        emissions=world2.emissions,
    )

    return world3, updated_agents, actions_with_traces


def simulate(
    world0: WorldState, agents0: list[AgentState], years: list[int]
) -> list[tuple[WorldState, list[AgentState], list[Action]]]:
    """Run the simulation over a list of years.

    Returns a history list where each element contains the world
    state after the step, the list of agent states and the actions taken.
    """
    world = world0
    agents = agents0
    history: list[tuple[WorldState, list[AgentState], list[Action]]] = []
    for _ in years:
        world, agents, actions = step(world, agents)
        history.append((world, agents, actions))
    return history
