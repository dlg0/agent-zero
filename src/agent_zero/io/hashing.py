"""Generate deterministic run identifiers based on run inputs.

The run ID is a short hash computed from the engine version, the
assumptions pack hash, the scenario pack hash, the list of years and
the random seed. This ensures reproducibility and provides a unique
directory name for results.
"""

from __future__ import annotations

import hashlib
import json


def make_run_id(
    engine_version: str,
    assumptions_hash: str,
    scenario_hash: str | None,
    years: list[int],
    seed: int,
    opts: dict | None = None,
) -> str:
    """Compute a deterministic run identifier.

    Parameters
    ----------
    engine_version : str
        The version of the simulation engine.
    assumptions_hash : str
        The hash of the baseline assumptions pack.
    scenario_hash : Optional[str]
        The hash of the scenario pack (or None for baseline only).
    years : List[int]
        The list of years included in the run.
    seed : int
        A random seed (currently unused but part of the id).
    opts : Optional[dict]
        Additional options to include in the hash (reserved for future use).

    Returns
    -------
    str
        A hexadecimal string truncated to 12 characters.
    """
    payload = {
        "engine_version": engine_version,
        "assumptions_hash": assumptions_hash,
        "scenario_hash": scenario_hash,
        "years": years,
        "seed": seed,
        "opts": opts or {},
    }
    # JSON serialisation ensures stable ordering
    serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()
    return digest[:12]
