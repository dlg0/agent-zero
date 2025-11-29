"""Integration tests for validation routines using real production data."""

from __future__ import annotations

import pytest

from agent_zero.io.validate import validate_assumptions_pack, validate_scenario_pack


@pytest.mark.integration
def test_validate_baseline_ok(baseline_pack: dict) -> None:
    """Verify the baseline assumptions pack passes validation."""
    errors = validate_assumptions_pack(baseline_pack)

    assert errors == [], f"Baseline pack validation failed: {errors}"


@pytest.mark.integration
def test_validate_scenario_ok(fast_elec_pack: dict) -> None:
    """Verify the fast-elec scenario pack passes validation."""
    errors = validate_scenario_pack(fast_elec_pack)

    assert errors == [], f"Scenario pack validation failed: {errors}"
