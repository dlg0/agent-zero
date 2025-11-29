"""Apply scenario patches to assumptions and policy tables.

Patches specify a target table (assumptions or policy), a set of
dimension values, an operation (replace, scale, add) and a new value.
Matching rows in the target table are located by equality on all
dimension columns specified (region, sector, tech, year, param),
ignoring any dimensions that are null in the patch. If no matching
rows are found and the operation is replace, a new row is added.
"""

from __future__ import annotations

from typing import Tuple
import pandas as pd

# list of dimension columns used to match rows; must appear in both
# assumptions and policy tables
DIM_COLS = ["region", "sector", "tech", "year", "param"]


def _ensure_dim_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all dimension columns exist in the dataframe.

    Missing columns are added with null values.
    """
    for c in DIM_COLS:
        if c not in df.columns:
            df[c] = None
    return df


def apply_patches(
    assumptions: pd.DataFrame, policy: pd.DataFrame, patches: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Apply scenario patches to the assumptions and policy tables.

    Returns a tuple of (new_assumptions, new_policy). The input
    dataframes are not modified; copies are created for updates.
    """
    # Work on copies to avoid side effects
    assumptions = _ensure_dim_cols(assumptions.copy())
    policy = _ensure_dim_cols(policy.copy())
    patches = _ensure_dim_cols(patches.copy())

    for _, row in patches.iterrows():
        target = row["target"]
        op = row["operation"]
        # Build a boolean mask for matching dimension values
        if target == "assumptions":
            base = assumptions
        else:
            base = policy
        mask = pd.Series(True, index=base.index)
        for c in DIM_COLS:
            val = row[c]
            # skip NaN/None in patch
            if pd.isna(val):
                continue
            mask &= base[c] == val
        # Determine rows that match
        matches = base[mask]
        if op == "replace":
            if not matches.empty:
                # replace values in matching rows
                base.loc[matches.index, "value"] = row["value"]
            else:
                # if no match, append a new row with dimension values and value
                new_row = {**{c: row[c] for c in base.columns if c in DIM_COLS},
                           "value": row["value"],
                           "unit": row["unit"],
                           # include param in assumptions and policy row if not None
                           "param": row.get("param"),
                           }
                # ensure all columns present in the new row
                for col in base.columns:
                    if col not in new_row:
                        new_row[col] = None
                # concat rather than deprecated DataFrame.append
                base = pd.concat([base, pd.DataFrame([new_row])], ignore_index=True)
        elif op == "scale":
            base.loc[matches.index, "value"] = base.loc[matches.index, "value"] * row["value"]
        elif op == "add":
            base.loc[matches.index, "value"] = base.loc[matches.index, "value"] + row["value"]
        # assign base back
        if target == "assumptions":
            assumptions = base
        else:
            policy = base
    return assumptions, policy