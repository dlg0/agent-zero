"""Integration test for the simulation loop."""

from pathlib import Path
from agent_zero.io.load_pack import load_assumptions_pack
from agent_zero.model.world import init_world
from agent_zero.model.agents import init_agents
from agent_zero.model.simulate import simulate


def test_simulation_runs_two_steps():
    # load baseline assumptions and policy
    ap = load_assumptions_pack(Path('data/assumptions_packs/baseline-v1'))
    assumptions = ap['assumptions']
    policy = ap['policy']
    # init world and agents
    world0 = init_world(assumptions, policy, start_year=2025)
    agents0 = init_agents(assumptions, start_year=2025)
    # run two years: 2025 and 2026
    history = simulate(world0, agents0, years=[2025, 2026])
    # two entries expected
    assert len(history) == 2
    # world years should be 2026 and 2027 (since t is incremented post step)
    years = [w.t for w, _, _ in history]
    assert years[0] == 2026
    assert years[1] == 2027
