"""Decision logic for agents in the toy model.

Each agent uses a simple forward‑looking rule to decide whether to
invest in additional capacity and how much to supply. Industrial
consumers adjust demand based on price. The regulator does not
directly act; its role is managed by the market clearing step.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..utils.types import Action, AgentState, WorldState


def _lookup_param(
    assumptions: pd.DataFrame, tech: str, year: int, param: str, default: float
) -> float:
    """Helper to lookup a parameter in the assumptions table using boolean indexing."""
    mask = (
        (assumptions["tech"] == tech)
        & (assumptions["year"] == year)
        & (assumptions["param"] == param)
    )
    if mask.any():
        return float(assumptions.loc[mask, "value"].iloc[0])
    return default


def _forecast_prices(current: float, trend_param: float, horizon: int) -> list[float]:
    """Forecast future prices using a linear trend."""
    return [current * (1 + trend_param * (y / horizon)) for y in range(1, horizon + 1)]


def _compute_npv(
    capex: float,
    opex: float,
    price_forecast: list[float],
    emissions_intensity: float,
    carbon_price: float,
    discount_rate: float,
) -> float:
    """Compute the net present value for investing in one unit of capacity."""
    npv = 0.0
    for y, p in enumerate(price_forecast, start=1):
        margin = p - opex - emissions_intensity * carbon_price
        npv += margin / ((1 + discount_rate) ** y)
    # subtract capex cost
    npv -= capex
    return npv


def decide(agent: AgentState, world: WorldState) -> Action:
    """Decide on the agent's action based on its type and the world state."""
    t = world.t
    assumptions = world.assumptions
    prices = world.prices
    # Regulator does nothing; carbon price is handled in market step
    if agent.agent_type == "Regulator":
        return Action(agent.id, {}, {}, {}, 0.0)

    if agent.agent_type in ("ElectricityProducer", "HydrogenProducer"):
        tech = agent.tech or ""
        # load parameters from assumptions or defaults
        capex = _lookup_param(assumptions, tech, t, "capex", 1000.0)
        opex = _lookup_param(assumptions, tech, t, "opex", 10.0)
        ei = _lookup_param(assumptions, tech, t, "emissions_intensity", 0.0)
        trend = _lookup_param(assumptions, tech, t, "trend_param", 0.0)
        dr = _lookup_param(assumptions, tech, t, "discount_rate", 0.07)
        invest_threshold = _lookup_param(assumptions, tech, t, "invest_threshold", 0.0)
        maxcap = _lookup_param(assumptions, tech, t, "max_capacity", np.inf)
        invest_step = _lookup_param(assumptions, tech, t, "invest_step", 10.0)

        H = agent.horizon
        # forecast future commodity price
        price_forecast = _forecast_prices(prices[tech], trend, H)
        npv = _compute_npv(capex, opex, price_forecast, ei, prices["carbon"], dr)

        invest_amt = 0.0
        if npv > invest_threshold and agent.capacity < maxcap:
            invest_amt = min(invest_step, maxcap - agent.capacity)

        supply_amt = agent.capacity  # supply equals existing capacity in v1
        emissions = supply_amt * ei
        return Action(
            agent_id=agent.id,
            supply={tech: supply_amt},
            invest={tech: invest_amt},
            retire={tech: 0.0},
            emissions=emissions,
        )

    if agent.agent_type == "IndustrialConsumer":
        # Consumers adjust demand based on electricity price relative to a reference
        ref_price = _lookup_param(assumptions, "electricity", t, "ref_price", 60.0)
        d_hi = _lookup_param(
            assumptions,
            "electricity",
            t,
            "demand_high",
            world.demand.get("electricity", 100.0),
        )
        d_lo = _lookup_param(
            assumptions,
            "electricity",
            t,
            "demand_low",
            0.8 * world.demand.get("electricity", 100.0),
        )
        _consumption = d_hi if prices["electricity"] < ref_price else d_lo
        # _consumption is modelled as negative supply (reserved for future use)
        return Action(
            agent_id=agent.id,
            supply={},
            invest={},
            retire={},
            emissions=0.0,
        )

    raise ValueError(f"Unknown agent type {agent.agent_type}")
