"""Unit tests for agent_zero.model.agents."""

from __future__ import annotations

import pandas as pd

from agent_zero.model.agents import init_agents


class TestInitAgents:
    """Tests for init_agents()."""

    def test_creates_four_agents(self, tiny_assumptions: pd.DataFrame):
        """init_agents() creates 4 agents."""
        agents = init_agents(tiny_assumptions, start_year=2025)
        assert len(agents) == 4

    def test_agent_types_correct(self, tiny_assumptions: pd.DataFrame):
        """init_agents() assigns correct agent types."""
        agents = init_agents(tiny_assumptions, start_year=2025)
        agent_types = {a.id: a.agent_type for a in agents}
        assert agent_types["EGEN1"] == "ElectricityProducer"
        assert agent_types["H2GEN1"] == "HydrogenProducer"
        assert agent_types["IND1"] == "IndustrialConsumer"
        assert agent_types["REG"] == "Regulator"

    def test_agent_ids_correct(self, tiny_assumptions: pd.DataFrame):
        """init_agents() assigns correct agent IDs."""
        agents = init_agents(tiny_assumptions, start_year=2025)
        ids = [a.id for a in agents]
        assert ids == ["EGEN1", "H2GEN1", "IND1", "REG"]

    def test_reads_initial_capacity_from_assumptions(self):
        """init_agents() reads initial_capacity from assumptions when present."""
        assumptions = pd.DataFrame(
            [
                {
                    "region": "AUS",
                    "sector": None,
                    "tech": "electricity",
                    "year": 2025,
                    "param": "initial_capacity",
                    "value": 500.0,
                    "unit": "MW",
                    "uncertainty_band": "mean",
                },
                {
                    "region": "AUS",
                    "sector": None,
                    "tech": "hydrogen",
                    "year": 2025,
                    "param": "initial_capacity",
                    "value": 50.0,
                    "unit": "MW",
                    "uncertainty_band": "mean",
                },
            ]
        )
        agents = init_agents(assumptions, start_year=2025)
        capacities = {a.id: a.capacity for a in agents}
        assert capacities["EGEN1"] == 500.0
        assert capacities["H2GEN1"] == 50.0

    def test_uses_default_capacities_when_not_in_assumptions(self):
        """init_agents() uses default capacities (100 for elec, 10 for hydrogen) when not in assumptions."""
        empty_assumptions = pd.DataFrame(
            columns=[
                "region",
                "sector",
                "tech",
                "year",
                "param",
                "value",
                "unit",
                "uncertainty_band",
            ]
        )
        agents = init_agents(empty_assumptions, start_year=2025)
        capacities = {a.id: a.capacity for a in agents}
        assert capacities["EGEN1"] == 100.0
        assert capacities["H2GEN1"] == 10.0
