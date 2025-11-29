"""Market clearing functions for the toy model.

Prices are updated using a simple proportional mechanism based on
supply–demand imbalances. Carbon prices are looked up from the
policy table for the current year. All markets are independent in v1.
"""

from __future__ import annotations

from typing import List
import pandas as pd

from ..utils.types import WorldState, Action


def clear_markets(world: WorldState, actions: List[Action]) -> WorldState:
    """Clear the electricity and hydrogen markets and update prices.

    The clearing rule adjusts prices proportionally to the excess
    supply (positive if supply exceeds demand, negative otherwise).
    Carbon price is set directly from the policy table. Emissions are
    aggregated from agent actions.
    """
    t = world.t
    prices = dict(world.prices)  # copy
    demand = dict(world.demand)

    # Sum supplies for each commodity
    supply_e = sum(a.supply.get("electricity", 0.0) for a in actions)
    supply_h = sum(a.supply.get("hydrogen", 0.0) for a in actions)

    # Price adjustment coefficients (arbitrary small numbers)
    k_e = 0.05
    k_h = 0.05

    # Compute imbalances (supply - demand)
    bal_e = supply_e - demand.get("electricity", 0.0)
    bal_h = supply_h - demand.get("hydrogen", 0.0)

    # Update prices; ensure non‑negative
    prices["electricity"] = max(0.0, prices["electricity"] + k_e * (-bal_e))
    prices["hydrogen"] = max(0.0, prices["hydrogen"] + k_h * (-bal_h))

    # Carbon price from policy
    # carbon price lookup without using query
    mask = (world.policy["year"] == t) & (world.policy["policy_type"] == "carbon_price")
    if mask.any():
        prices["carbon"] = float(world.policy.loc[mask, "value"].iloc[0])

    # Aggregate emissions
    total_emissions = sum(a.emissions for a in actions)

    flows = {
        "electricity_supply": supply_e,
        "hydrogen_supply": supply_h,
    }

    return WorldState(
        t=t,
        prices=prices,
        demand=demand,
        policy=world.policy,
        assumptions=world.assumptions,
        flows=flows,
        emissions=total_emissions,
    )