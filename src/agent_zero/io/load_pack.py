"""Routines to load assumptions and scenario packs from disk.

Packs are stored as directories under the `data/assumptions_packs` and
`data/scenario_packs` directories. Each pack must contain a
`manifest.yaml` file describing the contents. Assumptions packs also
contain `assumptions.csv` (or `.parquet`) and `policy.csv`; scenario packs
contain `scenario.yaml` and `patches.csv`.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import yaml


def load_manifest(pack_dir: Path) -> dict:
    """Load the manifest.yaml file from a pack directory."""
    manifest_path = pack_dir / "manifest.yaml"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_table(path: Path) -> pd.DataFrame:
    """Read a table from a Parquet or CSV file.

    If the Parquet file does not exist, looks for a CSV file with the same
    stem. If the Parquet engine is not available the function also falls back
    to reading a CSV file. This allows the package to run in environments
    without optional dependencies such as pyarrow or fastparquet.
    """
    # If path doesn't exist, try CSV extension
    if not path.exists():
        csv_path = path.with_suffix(".csv")
        if csv_path.exists():
            return pd.read_csv(csv_path)
    try:
        return pd.read_parquet(path)
    except Exception:
        # fall back to CSV; expect header row
        csv_path = path.with_suffix(".csv")
        return pd.read_csv(csv_path)


def load_assumptions_pack(pack_dir: Path) -> dict:
    """Load an assumptions pack from the given directory.

    Returns a dictionary with keys: manifest, assumptions, policy and dir.
    """
    man = load_manifest(pack_dir)
    assumptions_file = pack_dir / "assumptions.parquet"
    policy_file = pack_dir / "policy.parquet"
    assumptions = _read_table(assumptions_file)
    policy = _read_table(policy_file)
    return {
        "manifest": man,
        "assumptions": assumptions,
        "policy": policy,
        "dir": pack_dir,
    }


def load_scenario_pack(pack_dir: Path) -> dict:
    """Load a scenario pack from the given directory.

    Returns a dictionary with keys: manifest, scenario, patches and dir.
    """
    man = load_manifest(pack_dir)
    scenario_file = pack_dir / "scenario.yaml"
    with open(scenario_file, "r", encoding="utf-8") as f:
        scenario = yaml.safe_load(f)
    patches_file = pack_dir / "patches.parquet"
    # fallback to CSV if parquet engine unavailable
    patches = _read_table(patches_file)
    return {
        "manifest": man,
        "scenario": scenario,
        "patches": patches,
        "dir": pack_dir,
    }