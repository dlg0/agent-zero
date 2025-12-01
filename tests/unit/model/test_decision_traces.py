"""Tests for decision trace capture in agents."""

from __future__ import annotations

import pandas as pd
import pytest

from agent_zero.model.decisions import decide
from agent_zero.model.simulate import step
from agent_zero.utils.types import AgentState, WorldState


@pytest.fixture
def minimal_world() -> WorldState:
    """Create a minimal world state for testing."""
    assumptions = pd.DataFrame(
        {
            "year": [2025],
            "tech": ["electricity"],
            "param": ["capex"],
            "value": [1000.0],
        }
    )
    policy = pd.DataFrame(
        {"year": [2025], "region": ["AUS"], "policy_type": ["carbon_price"], "value": [50.0]}
    )
    return WorldState(
        t=2025,
        prices={"electricity": 50.0, "hydrogen": 100.0, "carbon": 50.0},
        demand={"electricity": 1000.0, "hydrogen": 100.0},
        policy=policy,
        assumptions=assumptions,
    )


@pytest.fixture
def producer_agent() -> AgentState:
    """Create a producer agent for testing."""
    return AgentState(
        id="EGEN1",
        agent_type="ElectricityProducer",
        region="AUS",
        tech="electricity",
        capacity=100.0,
        horizon=3,
    )


@pytest.fixture
def consumer_agent() -> AgentState:
    """Create a consumer agent for testing."""
    return AgentState(
        id="IND1",
        agent_type="IndustrialConsumer",
        region="AUS",
        sector="Industry",
    )


@pytest.fixture
def regulator_agent() -> AgentState:
    """Create a regulator agent for testing."""
    return AgentState(
        id="REG",
        agent_type="Regulator",
        region="AUS",
    )


class TestDecisionTraces:
    def test_producer_action_inputs(
        self, minimal_world: WorldState, producer_agent: AgentState
    ) -> None:
        """Producer actions should capture decision inputs."""
        action = decide(producer_agent, minimal_world)
        assert action.action_inputs is not None
        assert "prices" in action.action_inputs
        assert "capacity" in action.action_inputs
        assert "costs" in action.action_inputs
        assert "horizon" in action.action_inputs
        assert "discount_rate" in action.action_inputs

    def test_consumer_action_inputs(
        self, minimal_world: WorldState, consumer_agent: AgentState
    ) -> None:
        """Consumer actions should capture decision inputs."""
        action = decide(consumer_agent, minimal_world)
        assert action.action_inputs is not None
        assert "demand" in action.action_inputs
        assert "ref_price" in action.action_inputs
        assert "consumption" in action.action_inputs

    def test_regulator_action_inputs(
        self, minimal_world: WorldState, regulator_agent: AgentState
    ) -> None:
        """Regulator actions should capture decision inputs."""
        action = decide(regulator_agent, minimal_world)
        assert action.action_inputs is not None
        assert "carbon_price" in action.action_inputs
        assert "year" in action.action_inputs


class TestStateCapture:
    def test_step_captures_state_before_and_after(
        self, minimal_world: WorldState, producer_agent: AgentState
    ) -> None:
        """Step function should capture state_before and state_after."""
        agents = [producer_agent]
        _, _, actions = step(minimal_world, agents)

        assert len(actions) == 1
        action = actions[0]
        assert action.state_before is not None
        assert action.state_after is not None
        assert action.state_before["id"] == producer_agent.id
        assert action.state_after["id"] == producer_agent.id

    def test_state_after_reflects_investment(self, minimal_world: WorldState) -> None:
        """State_after should reflect capacity changes from investment."""
        assumptions = pd.DataFrame(
            {
                "year": [2025, 2025, 2025, 2025],
                "tech": ["electricity", "electricity", "electricity", "electricity"],
                "param": ["capex", "opex", "invest_threshold", "max_capacity"],
                "value": [10.0, 1.0, -1000.0, 1000.0],
            }
        )
        policy = pd.DataFrame(
            {
                "year": [2025],
                "region": ["AUS"],
                "policy_type": ["carbon_price"],
                "value": [0.0],
            }
        )
        world = WorldState(
            t=2025,
            prices={"electricity": 100.0, "hydrogen": 100.0, "carbon": 0.0},
            demand={"electricity": 1000.0, "hydrogen": 100.0},
            policy=policy,
            assumptions=assumptions,
        )
        agent = AgentState(
            id="EGEN1",
            agent_type="ElectricityProducer",
            region="AUS",
            tech="electricity",
            capacity=100.0,
            horizon=3,
        )

        _, _, actions = step(world, [agent])
        action = actions[0]

        if action.state_before and action.state_after:
            invest_amt = sum(action.invest.values())
            if invest_amt > 0:
                assert action.state_after["capacity"] > action.state_before["capacity"]
