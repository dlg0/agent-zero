"""Run the toy simulation through a sequence of years.

At each time step agents observe the world, decide on actions and
markets are cleared. New world and agent states are returned along
with the actions taken. A full run accumulates these tuples in
a history list.
"""

from __future__ import annotations

from typing import List, Tuple

from ..utils.types import WorldState, AgentState, Action
from .decisions import decide
from .markets import clear_markets


def step(
    world: WorldState, agents: List[AgentState]
) -> Tuple[WorldState, List[AgentState], List[Action]]:
    """Perform one simulation step.

    1. Each agent decides on an action given the current world state.
    2. Market clearing updates prices and aggregates flows and emissions.
    3. Agent capacities are updated according to their investment actions.
    4. Demand for the next year is updated from assumptions, if available.
    5. The time is advanced by one year.
    """
    # 1. Agent decisions
    actions: List[Action] = [decide(a, world) for a in agents]

    # 2. Market clearing
    world2 = clear_markets(world, actions)

    # 3. Update agent capacities with their investments
    updated_agents: List[AgentState] = []
    for ag in agents:
        act = next((x for x in actions if x.agent_id == ag.id), None)
        if act and ag.agent_type in ("ElectricityProducer", "HydrogenProducer"):
            tech = ag.tech or ""
            ag.capacity += act.invest.get(tech, 0.0)
        updated_agents.append(ag)

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

    return world3, updated_agents, actions


def simulate(
    world0: WorldState, agents0: List[AgentState], years: List[int]
) -> List[Tuple[WorldState, List[AgentState], List[Action]]]:
    """Run the simulation over a list of years.

    Returns a history list where each element contains the world
    state after the step, the list of agent states and the actions taken.
    """
    world = world0
    agents = agents0
    history: List[Tuple[WorldState, List[AgentState], List[Action]]] = []
    for _ in years:
        world, agents, actions = step(world, agents)
        history.append((world, agents, actions))
    return history