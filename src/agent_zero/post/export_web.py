"""Export a run bundle to web-friendly JSON format.

This module converts the Parquet-based run bundle into JSON files
suitable for consumption by the SvelteKit web frontend.

Bundle structure:
    web/runs/<run_id>/
    ├── manifest.json          # Run metadata, IDs, hashes
    ├── summary.json           # Headline metrics, cards data
    ├── timeseries.json        # Denormalised timeseries for charts
    ├── agents.json            # Agent catalogue + configs
    ├── agent_traces.json      # Decision traces per agent
    ├── assumptions_used.json  # Assumptions relevant to this run
    ├── scenario_diff.json     # Diff from baseline (if scenario run)
    ├── drivers.json           # Ranked factors driving results
    └── downloads/             # Symlinks or copies of raw files
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

import pandas as pd
import yaml

from agent_zero import __version__ as ENGINE_VERSION
from agent_zero.io.apply_patches import apply_patches
from agent_zero.io.load_pack import load_assumptions_pack, load_scenario_pack

logger = logging.getLogger(__name__)


def _safe_json_parse(value: str | dict | None, default: dict | None = None) -> dict:
    """Safely parse a JSON string or return the value if already a dict."""
    if default is None:
        default = {}
    if not value:
        return default
    if isinstance(value, dict):
        return value
    try:
        result = json.loads(value)
        return result if result else default
    except (json.JSONDecodeError, TypeError):
        return default


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_json(path: Path) -> dict:
    """Load a JSON file and return its contents."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: object) -> None:
    """Write data to a JSON file with indentation."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _read_parquet_safe(path: Path) -> pd.DataFrame:
    """Read a Parquet file, falling back to CSV if Parquet doesn't exist."""
    if path.exists():
        return pd.read_parquet(path)
    csv_path = path.with_suffix(".csv")
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()


def _build_reproduction_command(manifest: dict) -> str:
    """Build a CLI command to reproduce this run."""
    parts = ["agentzero", "run"]

    assumptions = manifest.get("assumptions") or manifest.get("assumptions_manifest") or {}
    assum_id = assumptions.get("id") or assumptions.get("name", "baseline")
    parts.extend(["--assum", assum_id])

    scenario = manifest.get("scenario") or manifest.get("scenario_manifest")
    if scenario and scenario.get("id"):
        parts.extend(["--scen", scenario["id"]])

    years = manifest.get("years", {})
    if isinstance(years, dict):
        start = years.get("start")
        end = years.get("end")
        step = years.get("step", 1)
        if start and end:
            if step == 1:
                parts.extend(["--years", f"{start}:{end}"])
            else:
                parts.extend(["--years", f"{start}:{step}:{end}"])
    elif isinstance(years, list) and years:
        parts.extend(["--years", ",".join(str(y) for y in sorted(years))])

    seed = manifest.get("seed")
    if seed is not None:
        parts.extend(["--seed", str(seed)])

    return " ".join(parts)


def _convert_manifest(manifest: dict, run_id: str) -> dict:
    """Convert internal manifest format to web schema."""
    years = manifest.get("years", {})
    if isinstance(years, list) and years:
        years_dict = {"start": min(years), "end": max(years)}
    elif isinstance(years, dict):
        years_dict = years
    else:
        years_dict = {"start": 2024, "end": 2050}

    assumptions = manifest.get("assumptions") or manifest.get("assumptions_manifest") or {}
    scenario = manifest.get("scenario") or manifest.get("scenario_manifest")

    web_manifest = {
        "run_id": run_id,
        "created_at": manifest.get("run_timestamp") or manifest.get("created_at", ""),
        "engine_version": manifest.get("engine_version", ENGINE_VERSION),
        "commit_hash": manifest.get("commit_hash"),
        "years": years_dict,
        "assumptions": {
            "id": assumptions.get("id") or assumptions.get("name", "unknown"),
            "version": assumptions.get("version", "1.0.0"),
            "hash": assumptions.get("hash", ""),
        },
        "scenario": (
            {
                "id": scenario["id"],
                "version": scenario.get("version", "1.0.0"),
                "hash": scenario.get("hash", ""),
            }
            if scenario and scenario.get("id")
            else None
        ),
        "seed": manifest.get("seed", 0),
        "reproduction_command": manifest.get("cli_command")
        or _build_reproduction_command(manifest),
        "schema_versions": manifest.get(
            "schema_versions",
            {"assumptions": "1.0.0", "scenario": None, "results": "1.0.0"},
        ),
        "units": manifest.get(
            "units",
            {
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
                },
            },
        ),
    }
    return web_manifest


def _extract_agents(agent_df: pd.DataFrame) -> list[dict]:
    """Extract unique agent configurations from agent_states DataFrame."""
    if agent_df.empty:
        return []

    agents: list[dict] = []
    seen_ids: set[str] = set()

    for _, row in agent_df.iterrows():
        agent_id = row.get("agent_id", "")
        if agent_id in seen_ids:
            continue
        seen_ids.add(agent_id)

        other_vars = _safe_json_parse(row.get("other_state_vars"))

        agents.append(
            {
                "agent_id": agent_id,
                "agent_type": row.get("agent_type", ""),
                "region": row.get("region", ""),
                "sector": other_vars.get("sector"),
                "tech": other_vars.get("tech"),
                "initial_capacity": float(row.get("capacity", 0)),
                "horizon": other_vars.get("horizon", 3),
                "discount_rate": 0.07,
                "decision_rule": "npv_threshold",
                "vintage": other_vars.get("vintage", 2024),
                "params": other_vars.get("params", {}),
            }
        )

    return agents


def _extract_agent_traces(agent_df: pd.DataFrame) -> list[dict]:
    """Extract decision traces from agent_states DataFrame."""
    if agent_df.empty:
        return []

    traces: list[dict] = []

    for _, row in agent_df.iterrows():
        action_inputs = _safe_json_parse(row.get("action_inputs"))
        state_before = _safe_json_parse(row.get("state_before"))
        state_after = _safe_json_parse(row.get("state_after"))
        action_data = _safe_json_parse(row.get("action"))

        action = _determine_action(action_data)

        traces.append(
            {
                "agent_id": row.get("agent_id", ""),
                "year": int(row.get("year", 0)),
                "action": action,
                "action_inputs": {
                    "current_price": action_inputs.get("current_price", 0.0),
                    "expected_price": row.get("expected_price")
                    if pd.notna(row.get("expected_price"))
                    else None,
                    "npv": action_inputs.get("npv"),
                    "capacity_headroom": action_inputs.get("capacity_headroom"),
                    "carbon_price": action_inputs.get("carbon_price", 0.0),
                },
                "state_before": {
                    "capacity": state_before.get("capacity", 0.0),
                    "cash": state_before.get("cash", 0.0),
                    "vintage": state_before.get("vintage", 2024),
                },
                "state_after": {
                    "capacity": state_after.get("capacity", row.get("capacity", 0.0)),
                    "cash": state_after.get("cash", 0.0),
                    "vintage": state_after.get("vintage", 2024),
                    "investment": float(row.get("investment", 0)),
                    "supply": action_data.get("supply", {}),
                    "emissions": action_data.get("emissions", 0.0),
                },
            }
        )

    return traces


def _determine_action(action_data: dict) -> str:
    """Determine the action type from action data."""
    if action_data.get("invest") and any(v > 0 for v in action_data["invest"].values()):
        return "invest"
    if action_data.get("retire") and any(v > 0 for v in action_data["retire"].values()):
        return "retire"
    if action_data.get("supply") and any(v > 0 for v in action_data["supply"].values()):
        return "supply"
    return "hold"


def _load_assumptions_used(manifest: dict) -> list[dict]:
    """Resolve the assumptions used for this run into AssumptionRow dicts.

    Uses the same pack + patch logic as the CLI (build/run commands),
    based on the assumptions/scenario IDs recorded in the run manifest.
    """
    assum_meta = manifest.get("assumptions") or manifest.get("assumptions_manifest") or {}
    assum_id = assum_meta.get("id")
    if not assum_id:
        logger.warning("No assumptions ID found in manifest, skipping assumptions export")
        return []

    pack_dir = Path("data") / "assumptions_packs" / assum_id
    if not pack_dir.exists():
        logger.warning(f"Assumptions pack not found at {pack_dir}, skipping assumptions export")
        return []

    try:
        ap = load_assumptions_pack(pack_dir)
        assumptions_df = ap["assumptions"]
        policy_df = ap["policy"]
    except Exception as e:
        logger.warning(f"Failed to load assumptions pack {assum_id}: {e}")
        return []

    scen_meta = manifest.get("scenario") or manifest.get("scenario_manifest") or {}
    scen_id = scen_meta.get("id")
    if scen_id:
        scen_dir = Path("data") / "scenario_packs" / scen_id
        if scen_dir.exists():
            try:
                sp = load_scenario_pack(scen_dir)
                assumptions_df, policy_df = apply_patches(assumptions_df, policy_df, sp["patches"])
            except Exception as e:
                logger.warning(f"Failed to apply scenario patches from {scen_id}: {e}")

    if assumptions_df.empty:
        return []

    rows: list[dict] = []
    for _, row in assumptions_df.iterrows():
        rows.append(
            {
                "param": row.get("param"),
                "region": row.get("region") if pd.notna(row.get("region")) else None,
                "sector": row.get("sector") if pd.notna(row.get("sector")) else None,
                "tech": row.get("tech") if pd.notna(row.get("tech")) else None,
                "year": int(row.get("year")) if pd.notna(row.get("year")) else 0,
                "value": float(row.get("value")) if pd.notna(row.get("value")) else 0.0,
                "unit": row.get("unit", "") or "",
                "source": row.get("source")
                if "source" in row and pd.notna(row.get("source"))
                else None,
            }
        )

    return rows


def export_web_bundle(run_dir: Path, out_dir: Path) -> None:
    """Export a run bundle to web-friendly JSON format.

    Parameters
    ----------
    run_dir : Path
        Path to the run bundle directory containing manifest.yaml,
        timeseries.parquet, agent_states.parquet, and summary.json.
    out_dir : Path
        Path to the output directory where web bundle will be written.

    Raises
    ------
    FileNotFoundError
        If required files are missing from run_dir.
    """
    run_dir = Path(run_dir)
    out_dir = Path(out_dir)

    manifest_path = run_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.yaml not found in {run_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_yaml(manifest_path)
    run_id = manifest.get("run_id", run_dir.name)

    web_manifest = _convert_manifest(manifest, run_id)
    _write_json(out_dir / "manifest.json", web_manifest)

    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        summary = _load_json(summary_path)
        _write_json(out_dir / "summary.json", summary)
    else:
        _write_json(out_dir / "summary.json", {"run_id": run_id})

    ts_df = _read_parquet_safe(run_dir / "timeseries.parquet")
    if not ts_df.empty:
        timeseries = ts_df.to_dict(orient="records")
        _write_json(out_dir / "timeseries.json", timeseries)
    else:
        _write_json(out_dir / "timeseries.json", [])

    agent_df = _read_parquet_safe(run_dir / "agent_states.parquet")
    agents = _extract_agents(agent_df)
    _write_json(out_dir / "agents.json", agents)

    agent_traces = _extract_agent_traces(agent_df)
    _write_json(out_dir / "agent_traces.json", agent_traces)

    assumptions_used = _load_assumptions_used(manifest)
    _write_json(out_dir / "assumptions_used.json", assumptions_used)

    scenario = manifest.get("scenario") or manifest.get("scenario_manifest")
    if scenario and scenario.get("id"):
        _write_json(out_dir / "scenario_diff.json", [])

    # drivers.json is intentionally empty until story generation populates it.
    # The frontend shows "No drivers data available. Run story generation to populate."
    # which is the expected UX for runs that haven't had story generation run.
    _write_json(out_dir / "drivers.json", [])

    downloads_dir = out_dir / "downloads"
    downloads_dir.mkdir(exist_ok=True)

    for fname in ["timeseries.parquet", "agent_states.parquet"]:
        src = run_dir / fname
        dst = downloads_dir / fname
        if src.exists():
            try:
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                os.symlink(src.resolve(), dst)
            except OSError:
                shutil.copy2(src, dst)


def rebuild_web_index(web_dir: Path) -> None:
    """Rebuild runs/index.json from all exported runs.

    Scans web_dir/runs/*/manifest.json and creates web_dir/runs/index.json.

    Parameters
    ----------
    web_dir : Path
        Path to the web directory containing runs/.
    """
    web_dir = Path(web_dir)
    runs_dir = web_dir / "runs" if web_dir.name != "runs" else web_dir

    if web_dir.name == "runs":
        runs_dir = web_dir
        index_path = web_dir / "index.json"
    else:
        runs_dir = web_dir / "runs"
        index_path = runs_dir / "index.json"

    if not runs_dir.exists():
        _write_json(index_path, [])
        return

    entries: list[dict] = []

    for run_path in sorted(runs_dir.iterdir()):
        if not run_path.is_dir():
            continue
        manifest_path = run_path / "manifest.json"
        if not manifest_path.exists():
            continue

        try:
            manifest = _load_json(manifest_path)
        except (json.JSONDecodeError, OSError):
            continue

        summary_path = run_path / "summary.json"
        quick_summary = {"cumulative_emissions": 0, "year_net_zero": None}
        if summary_path.exists():
            try:
                summary = _load_json(summary_path)
                quick_summary = {
                    "cumulative_emissions": summary.get("cumulative_emissions", 0),
                    "year_net_zero": summary.get("year_net_zero"),
                }
            except (json.JSONDecodeError, OSError):
                pass

        scenario = manifest.get("scenario")
        tags = []
        if scenario:
            tags.append("scenario")
        else:
            tags.append("baseline")

        entries.append(
            {
                "run_id": manifest.get("run_id", run_path.name),
                "created_at": manifest.get("created_at", ""),
                "years": manifest.get("years", {"start": 2024, "end": 2050}),
                "assumptions_id": manifest.get("assumptions", {}).get("id", "unknown"),
                "scenario_id": scenario.get("id") if scenario else None,
                "engine_version": manifest.get("engine_version", "0.1.0"),
                "quick_summary": quick_summary,
                "tags": tags,
            }
        )

    entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)

    _write_json(index_path, entries)
