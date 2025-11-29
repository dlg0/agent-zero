"""Integration tests for the simulation engine using real production data."""

from __future__ import annotations

import pytest

from agent_zero.model.simulate import simulate
from agent_zero.utils.types import Action, AgentState, WorldState


@pytest.mark.integration
def test_simulation_runs_two_steps(
    baseline_world_agents: tuple[WorldState, list[AgentState]],
) -> None:
    """Verify simulate() runs two steps without error."""
    world0, agents0 = baseline_world_agents
    years = [2025, 2026]

    history = simulate(world0, agents0, years)

    assert len(history) == 2


@pytest.mark.integration
def test_simulation_history_structure(
    baseline_world_agents: tuple[WorldState, list[AgentState]],
) -> None:
    """Verify each history entry is a tuple of (world, agents, actions)."""
    world0, agents0 = baseline_world_agents
    years = [2025]

    history = simulate(world0, agents0, years)

    assert len(history) == 1
    world, agents, actions = history[0]
    assert isinstance(world, WorldState)
    assert isinstance(agents, list)
    assert all(isinstance(a, AgentState) for a in agents)
    assert isinstance(actions, list)
    assert all(isinstance(a, Action) for a in actions)


@pytest.mark.integration
def test_simulation_time_advances(
    baseline_world_agents: tuple[WorldState, list[AgentState]],
) -> None:
    """Verify world.t increments correctly each step."""
    world0, agents0 = baseline_world_agents
    start_t = world0.t
    years = [2025, 2026, 2027]

    history = simulate(world0, agents0, years)

    for i, (world, _, _) in enumerate(history):
        expected_t = start_t + i + 1
        assert world.t == expected_t, f"Step {i}: expected t={expected_t}, got t={world.t}"
