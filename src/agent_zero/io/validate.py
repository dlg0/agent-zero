"""Validation routines for assumptions and scenario packs.

These functions perform lightweight checks to ensure required columns
exist and that operations and targets in scenario patches are valid.
The v1 rules are deliberately minimal; stricter validation can be
introduced in future versions.
"""

from __future__ import annotations

import pandas as pd

# Required columns for assumptions and policy tables
REQ_ASSUM_COLS = {"region", "year", "param", "value", "unit", "uncertainty_band"}
REQ_POLICY_COLS = {"region", "year", "policy_type", "value", "unit"}

# Required columns for scenario patches
REQ_PATCH_COLS = {
    "target",
    "region",
    "year",
    "param",
    "operation",
    "value",
    "unit",
    "rationale",
}

ALLOWED_PATCH_OPS = {"replace", "scale", "add"}
ALLOWED_PATCH_TARGETS = {"assumptions", "policy"}


def validate_assumptions_pack(pack: dict) -> list[str]:
    """Validate an assumptions pack.

    Returns a list of error messages; an empty list indicates success.
    Only basic column presence and missing unit checks are performed.
    """
    errs: list[str] = []
    assumptions: pd.DataFrame = pack["assumptions"]
    policy: pd.DataFrame = pack["policy"]

    missing_assum_cols = REQ_ASSUM_COLS - set(assumptions.columns)
    if missing_assum_cols:
        errs.append(f"assumptions missing columns: {missing_assum_cols}")
    missing_policy_cols = REQ_POLICY_COLS - set(policy.columns)
    if missing_policy_cols:
        errs.append(f"policy missing columns: {missing_policy_cols}")
    if assumptions["unit"].isna().any():
        errs.append("assumptions table has empty unit values")
    if policy["unit"].isna().any():
        errs.append("policy table has empty unit values")
    return errs


def validate_scenario_pack(pack: dict) -> list[str]:
    """Validate a scenario pack.

    Returns a list of error messages; an empty list indicates success.
    Checks for required columns and allowed operations and targets.
    """
    errs: list[str] = []
    patches: pd.DataFrame = pack["patches"]
    missing_patch_cols = REQ_PATCH_COLS - set(patches.columns)
    if missing_patch_cols:
        errs.append(f"patches missing columns: {missing_patch_cols}")
    bad_ops = set(patches["operation"]) - ALLOWED_PATCH_OPS
    if bad_ops:
        errs.append(f"patches contain invalid operations: {bad_ops}")
    bad_targets = set(patches["target"]) - ALLOWED_PATCH_TARGETS
    if bad_targets:
        errs.append(f"patches contain invalid targets: {bad_targets}")
    if patches["unit"].isna().any():
        errs.append("patches table has empty unit values")
    return errs
