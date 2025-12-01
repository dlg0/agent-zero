"""Write the run history to a results bundle on disk.

A results bundle consists of:
  - a timeseries Parquet file with prices, supplies, demand and emissions
  - an agent states Parquet file capturing capacity evolution
  - a summary JSON with headline metrics
  - a manifest YAML with references back to the input packs
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

from agent_zero import __version__ as ENGINE_VERSION

from ..utils.types import Action, AgentState, WorldState

UNITS = {
    "timeseries": {
        "year": None,
        "region": None,
        "commodity": None,
        "price": "USD/MWh",
        "demand": "MWh",
        "supply": "MWh",
        "emissions": "tCO2e",
    },
    "agent_states": {
        "year": None,
        "agent_id": None,
        "agent_type": None,
        "region": None,
        "capacity": "MW",
        "investment": "MW",
        "expected_price": "USD/MWh",
        "other_state_vars": None,
        "action": None,
        "action_inputs": None,
        "state_before": None,
        "state_after": None,
    },
}


def _extract_pack_ref(manifest: dict | None) -> dict | None:
    """Extract id, hash, version from a manifest for lineage tracking."""
    if manifest is None:
        return None
    return {
        "id": manifest.get("id"),
        "hash": manifest.get("hash"),
        "version": manifest.get("version"),
    }


def write_run_bundle(
    out_base: Path,
    run_id: str,
    history: list[tuple[WorldState, list[AgentState], list[Action]]],
    manifests: dict[str, dict],
    seed: int | None = None,
    cli_command: str | None = None,
) -> Path:
    """Write a run bundle to disk.

    Parameters
    ----------
    out_base : Path
        The directory into which to write the run. A subdirectory named
        after run_id is created.
    run_id : str
        The unique run identifier.
    history : list
        A list of tuples (world, agents, actions) for each step.
    manifests : dict
        A dictionary with 'assumptions' and optional 'scenario'
        manifest dictionaries.
    seed : int | None
        The random seed used for the run.
    cli_command : str | None
        The exact CLI command used to invoke this run.

    Returns
    -------
    Path
        The path to the run directory.
    """
    run_dir = out_base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    created_ts = datetime.now(UTC).isoformat()

    timeseries_rows: list[dict[str, float | int | str | None]] = []
    agent_rows = []
    # iterate over history and collect rows
    for world, agents, actions in history:
        t = world.t
        # Build supply per (region, commodity) from Action.supply dicts
        supply_by_rc: dict[tuple[str, str], float] = {}
        for ag, act in zip(agents, actions, strict=True):
            for commodity, amt in act.supply.items():
                key = (ag.region, commodity)
                supply_by_rc[key] = supply_by_rc.get(key, 0.0) + amt

        # Get commodities (excluding "carbon" - it's a policy param, not traded)
        commodities = [c for c in world.prices if c != "carbon"]
        regions = {ag.region for ag in agents}

        # Emit one row per (region, commodity) - long format
        for region in regions:
            for commodity in commodities:
                timeseries_rows.append(
                    {
                        "year": t,
                        "region": region,
                        "commodity": commodity,
                        "price": world.prices[commodity],
                        "demand": world.demand.get(commodity, 0.0),
                        "supply": supply_by_rc.get((region, commodity), 0.0),
                        "emissions": world.emissions,
                        "scenario_id": manifests.get("scenario", {}).get("id")
                        if manifests.get("scenario")
                        else None,
                        "assumptions_id": manifests.get("assumptions", {}).get("id"),
                        "run_id": run_id,
                    }
                )
        # agent rows: capacity etc.
        for ag, act in zip(agents, actions, strict=True):
            total_investment = sum(act.invest.values())
            other_state_vars = json.dumps(
                {
                    "sector": ag.sector,
                    "tech": ag.tech,
                    "cash": ag.cash,
                    "horizon": ag.horizon,
                    "vintage": ag.vintage,
                    "params": ag.params,
                }
            )
            action_summary = json.dumps(
                {
                    "supply": act.supply,
                    "invest": act.invest,
                    "retire": act.retire,
                    "emissions": act.emissions,
                }
            )
            action_inputs_json = json.dumps(act.action_inputs) if act.action_inputs else None
            state_before_json = json.dumps(act.state_before) if act.state_before else None
            state_after_json = json.dumps(act.state_after) if act.state_after else None
            agent_rows.append(
                {
                    "year": t,
                    "agent_id": ag.id,
                    "agent_type": ag.agent_type,
                    "region": ag.region,
                    "capacity": ag.capacity,
                    "investment": total_investment,
                    "expected_price": act.expected_price,
                    "other_state_vars": other_state_vars,
                    "action": action_summary,
                    "action_inputs": action_inputs_json,
                    "state_before": state_before_json,
                    "state_after": state_after_json,
                }
            )

    ts_df = pd.DataFrame(timeseries_rows)
    ag_df = pd.DataFrame(agent_rows)

    # Write Parquet if supported; fall back to CSV when parquet engines are unavailable
    ts_path = run_dir / "timeseries.parquet"
    ag_path = run_dir / "agent_states.parquet"
    try:
        ts_df.to_parquet(ts_path, index=False)
    except Exception:
        # use CSV fallback
        ts_path = run_dir / "timeseries.csv"
        ts_df.to_csv(ts_path, index=False)
    try:
        ag_df.to_parquet(ag_path, index=False)
    except Exception:
        ag_path = run_dir / "agent_states.csv"
        ag_df.to_csv(ag_path, index=False)

    # Compute summary metrics
    # Emissions are repeated per commodity row, so deduplicate by (year, region)
    if not ts_df.empty:
        emissions_by_yr = ts_df.groupby(["year", "region"])["emissions"].first()
        cumulative_emissions = float(emissions_by_yr.sum())
        peak_emissions = float(emissions_by_yr.max())
        if not emissions_by_yr.empty:
            min_emissions_idx = emissions_by_yr.idxmin()
            year_net_zero: int | None = int(min_emissions_idx[0])  # type: ignore[index]
        else:
            year_net_zero = None
    else:
        cumulative_emissions = 0.0
        peak_emissions = 0.0
        year_net_zero = None

    # Average prices by commodity
    avg_prices = ts_df.groupby("commodity")["price"].mean().to_dict() if not ts_df.empty else {}

    # Investment totals from agent states
    if not ag_df.empty:
        total_investment = float(ag_df["investment"].sum())
        by_agent_type = ag_df.groupby("agent_type")["investment"].sum().to_dict()
        investment_totals = {"total": total_investment, "by_agent_type": by_agent_type}
    else:
        investment_totals = {"total": 0.0, "by_agent_type": {}}

    # Peak capacity by agent type
    peak_capacity = (
        ag_df.groupby("agent_type")["capacity"].max().to_dict() if not ag_df.empty else {}
    )

    # Security of supply per commodity
    def compute_security_of_supply(
        df: pd.DataFrame,
    ) -> dict[str, dict[str, float]]:
        security: dict[str, dict[str, float]] = {}
        if df.empty:
            return security
        for commodity in df["commodity"].unique():
            cdf = df[df["commodity"] == commodity]
            yearly = cdf.groupby("year").agg({"supply": "sum", "demand": "sum"})
            shortage_years = (yearly["supply"] < yearly["demand"]).sum()
            shortage_freq = float(shortage_years / len(yearly)) if len(yearly) > 0 else 0.0
            ratios = yearly["supply"] / yearly["demand"].replace(0, float("inf"))
            min_ratio = float(ratios.min()) if not ratios.empty else 1.0
            security[commodity] = {
                "shortage_frequency": shortage_freq,
                "min_supply_demand_ratio": min_ratio,
            }
        return security

    security_of_supply = compute_security_of_supply(ts_df)

    summary = {
        "run_id": run_id,
        "created": created_ts,
        "cumulative_emissions": cumulative_emissions,
        "average_prices": avg_prices,
        "investment_totals": investment_totals,
        "peak_capacity": peak_capacity,
        "peak_emissions": peak_emissions,
        "year_net_zero": year_net_zero,
        "security_of_supply": security_of_supply,
    }
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Build lineage manifest per results spec
    years = sorted(int(y) for y in ts_df["year"].unique()) if not ts_df.empty else []

    schema_versions = {
        "assumptions": manifests.get("assumptions", {}).get("schema_version"),
        "scenario": manifests.get("scenario", {}).get("schema_version")
        if manifests.get("scenario")
        else None,
        "results": "1.0.0",
    }

    run_manifest = {
        "run_id": run_id,
        "run_timestamp": created_ts,
        "engine_version": ENGINE_VERSION,
        "seed": seed,
        "years": years,
        "assumptions": _extract_pack_ref(manifests.get("assumptions")),
        "scenario": _extract_pack_ref(manifests.get("scenario")),
        "schema_versions": schema_versions,
        "units": UNITS,
        "cli_command": cli_command,
    }
    with open(run_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(run_manifest, f)

    return run_dir
