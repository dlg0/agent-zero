"""Write the run history to a results bundle on disk.

A results bundle consists of:
  - a timeseries Parquet file with prices, supplies, demand and emissions
  - an agent states Parquet file capturing capacity evolution
  - a summary JSON with headline metrics
  - a manifest YAML with references back to the input packs
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict
import json
from datetime import datetime
import pandas as pd
import yaml

from ..utils.types import WorldState, AgentState, Action


def write_run_bundle(
    out_base: Path,
    run_id: str,
    history: List[Tuple[WorldState, List[AgentState], List[Action]]],
    manifests: Dict[str, Dict],
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

    Returns
    -------
    Path
        The path to the run directory.
    """
    run_dir = out_base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    timeseries_rows = []
    agent_rows = []
    # iterate over history and collect rows
    for world, agents, actions in history:
        t = world.t
        # timeseries row: prices, flows, demand, emissions
        row = {"year": t}
        row.update({f"price_{k}": v for k, v in world.prices.items()})
        row.update(world.flows)
        row.update({f"demand_{k}": v for k, v in world.demand.items()})
        row["emissions"] = world.emissions
        timeseries_rows.append(row)
        # agent rows: capacity etc.
        for ag in agents:
            agent_rows.append({
                "year": t,
                "agent_id": ag.id,
                "agent_type": ag.agent_type,
                "region": ag.region,
                "sector": ag.sector,
                "tech": ag.tech,
                "capacity": ag.capacity,
                "cash": ag.cash,
                "horizon": ag.horizon,
            })

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

    # summary metrics: peak emissions and year net zero achieved (minimum emissions)
    summary = {
        "run_id": run_id,
        "created": datetime.utcnow().isoformat(),
        "peak_emissions": float(ts_df["emissions"].max()) if not ts_df.empty else 0.0,
        "year_net_zero": int(ts_df.loc[ts_df["emissions"].idxmin(), "year"]) if not ts_df.empty else None,
    }
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # manifest for run: include references to input manifests
    run_manifest = {
        "run_id": run_id,
        "assumptions_manifest": manifests.get("assumptions"),
        "scenario_manifest": manifests.get("scenario"),
    }
    with open(run_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(run_manifest, f)

    return run_dir