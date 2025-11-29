"""Tests for the patch application logic."""

import pandas as pd
from agent_zero.io.apply_patches import apply_patches


def test_replace_patch_adds_new_row_if_missing():
    # baseline table has one row
    assumptions = pd.DataFrame([{
        'region': 'AUS', 'sector': None, 'tech': 'electricity', 'year': 2025,
        'param': 'capex', 'value': 100.0, 'unit': 'X', 'uncertainty_band': 'mean'
    }])
    policy = pd.DataFrame([{
        'region': 'AUS', 'sector': None, 'year': 2025,
        'policy_type': 'carbon_price', 'value': 0.0, 'unit': 'X'
    }])
    # patch with missing match should add new row
    patches = pd.DataFrame([{
        'target': 'assumptions', 'region': 'AUS', 'sector': None, 'tech': 'hydrogen',
        'year': 2025, 'param': 'capex', 'operation': 'replace', 'value': 50.0,
        'unit': 'X', 'rationale': 'add new row'
    }])
    new_assum, new_policy = apply_patches(assumptions, policy, patches)
    # there should be two rows now
    assert len(new_assum) == 2
    # new row should have value 50
    added = new_assum.query("tech == 'hydrogen'")
    assert float(added['value'].iloc[0]) == 50.0
