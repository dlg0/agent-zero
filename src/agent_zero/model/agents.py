"""Create agent instances for the toy model.

For the minimal v1 implementation there are four agent classes:
  - An electricity producer
  - A hydrogen producer
  - A single industrial consumer
  - A regulator

Capacities can be specified in the assumptions table using the
'initial_capacity' parameter for each tech and region. If omitted a
default value is used.
"""

from __future__ import annotations

from typing import List
import pandas as pd

from ..utils.types import AgentState


def init_agents(assumptions: pd.DataFrame, start_year: int) -> List[AgentState]:
    """Initialise the agent state list.

    Reads initial capacities from the assumptions table. If not
    specified, defaults of 100 for electricity and 10 for hydrogen are
    used. All agents are created in region 'AUS'.
    """
    agents: List[AgentState] = []

    # helper to lookup parameters at start year using boolean indexing
    def get_param(tech: str, param: str, default: float) -> float:
        mask = (
            (assumptions["year"] == start_year)
            & (assumptions["tech"] == tech)
            & (assumptions["param"] == param)
        )
        if mask.any():
            return float(assumptions.loc[mask, "value"].iloc[0])
        return default

    elec_cap = get_param("electricity", "initial_capacity", 100.0)
    h2_cap = get_param("hydrogen", "initial_capacity", 10.0)

    # Electricity producer
    agents.append(
        AgentState(
            id="EGEN1",
            agent_type="ElectricityProducer",
            region="AUS",
            tech="electricity",
            capacity=elec_cap,
            vintage=start_year,
            cash=0.0,
            horizon=3,
        )
    )
    # Hydrogen producer
    agents.append(
        AgentState(
            id="H2GEN1",
            agent_type="HydrogenProducer",
            region="AUS",
            tech="hydrogen",
            capacity=h2_cap,
            vintage=start_year,
            cash=0.0,
            horizon=3,
        )
    )
    # Industrial consumer
    agents.append(
        AgentState(
            id="IND1",
            agent_type="IndustrialConsumer",
            region="AUS",
            sector="Industry",
            capacity=0.0,
            horizon=1,
        )
    )
    # Regulator
    agents.append(
        AgentState(
            id="REG",
            agent_type="Regulator",
            region="AUS",
            horizon=1,
        )
    )
    return agents