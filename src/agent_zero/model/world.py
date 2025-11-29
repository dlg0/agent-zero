"""Initialise the world state from assumptions and policy tables.

The world state encapsulates the current time, prices, demand and
policy parameters. It is immutable: each step creates a new world.
"""

from __future__ import annotations

import pandas as pd

from ..utils.types import WorldState
from .defaults import DEFAULT_DEMAND, DEFAULT_PRICES


def init_world(assumptions: pd.DataFrame, policy: pd.DataFrame, start_year: int) -> WorldState:
    """Create an initial world state from assumptions and policy.

    Looks up the carbon price from the policy table for the start year and
    overrides default demand if the assumptions specify a demand row for
    the commodity and year. Other prices and demand use defaults.
    """
    # Carbon price lookup from policy
    cp_mask = (policy["year"] == start_year) & (policy["policy_type"] == "carbon_price")
    if cp_mask.any():
        carbon = float(policy.loc[cp_mask, "value"].iloc[0])
    else:
        carbon = DEFAULT_PRICES["carbon"]
    prices: dict[str, float] = dict(DEFAULT_PRICES)
    prices["carbon"] = carbon

    demand: dict[str, float] = dict(DEFAULT_DEMAND)
    # override demand from assumptions if provided
    for commodity in ["electricity", "hydrogen"]:
        # 'tech' column indicates the commodity in this toy model
        mask = (
            (assumptions["year"] == start_year)
            & (assumptions["param"] == "demand")
            & (assumptions["tech"] == commodity)
        )
        if mask.any():
            demand[commodity] = float(assumptions.loc[mask, "value"].iloc[0])

    return WorldState(
        t=start_year,
        prices=prices,
        demand=demand,
        policy=policy,
        assumptions=assumptions,
    )
