"""Unit tests for agent_zero.model.world."""

from __future__ import annotations

import pandas as pd

from agent_zero.model.defaults import DEFAULT_DEMAND, DEFAULT_PRICES
from agent_zero.model.world import init_world


class TestInitWorld:
    """Tests for init_world()."""

    def test_sets_start_year_as_t(self, tiny_assumptions: pd.DataFrame, tiny_policy: pd.DataFrame):
        """init_world() sets the start year as t."""
        world = init_world(tiny_assumptions, tiny_policy, start_year=2025)
        assert world.t == 2025

    def test_extracts_carbon_price_from_policy(
        self, tiny_assumptions: pd.DataFrame, tiny_policy: pd.DataFrame
    ):
        """init_world() extracts carbon price from policy table for start year."""
        world = init_world(tiny_assumptions, tiny_policy, start_year=2026)
        assert world.prices["carbon"] == 25.0

    def test_uses_default_carbon_price_when_not_in_policy(self, tiny_assumptions: pd.DataFrame):
        """init_world() uses default carbon price when year not in policy."""
        empty_policy = pd.DataFrame(
            columns=["region", "sector", "year", "policy_type", "value", "unit"]
        )
        world = init_world(tiny_assumptions, empty_policy, start_year=2025)
        assert world.prices["carbon"] == DEFAULT_PRICES["carbon"]

    def test_extracts_demand_from_assumptions(
        self, tiny_assumptions: pd.DataFrame, tiny_policy: pd.DataFrame
    ):
        """init_world() extracts demand for electricity and hydrogen from assumptions."""
        world = init_world(tiny_assumptions, tiny_policy, start_year=2025)
        assert world.demand["electricity"] == 100.0
        assert world.demand["hydrogen"] == 10.0

    def test_uses_default_demand_when_not_in_assumptions(self, tiny_policy: pd.DataFrame):
        """init_world() uses default demand when not specified in assumptions."""
        minimal_assumptions = pd.DataFrame(
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
        world = init_world(minimal_assumptions, tiny_policy, start_year=2025)
        assert world.demand["electricity"] == DEFAULT_DEMAND["electricity"]
        assert world.demand["hydrogen"] == DEFAULT_DEMAND["hydrogen"]

    def test_world_contains_passed_dataframes(
        self, tiny_assumptions: pd.DataFrame, tiny_policy: pd.DataFrame
    ):
        """WorldState contains the passed assumptions and policy DataFrames."""
        world = init_world(tiny_assumptions, tiny_policy, start_year=2025)
        pd.testing.assert_frame_equal(world.assumptions, tiny_assumptions)
        pd.testing.assert_frame_equal(world.policy, tiny_policy)
