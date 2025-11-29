"""Unit tests for agent_zero.io.validate module."""

from __future__ import annotations

import pandas as pd

from agent_zero.io.validate import (
    validate_assumptions_pack,
    validate_scenario_pack,
)


class TestValidateAssumptionsPack:
    """Tests for validate_assumptions_pack()."""

    def test_valid_pack_returns_empty_errors(self, tiny_baseline_pack: dict) -> None:
        errors = validate_assumptions_pack(tiny_baseline_pack)
        assert errors == []

    def test_detects_missing_assumptions_columns(self) -> None:
        assumptions = pd.DataFrame(
            {
                "region": ["AUS"],
                "year": [2025],
                "param": ["capex"],
                "unit": ["AUD/kW"],
            }
        )
        policy = pd.DataFrame(
            {
                "region": ["AUS"],
                "year": [2025],
                "policy_type": ["carbon_price"],
                "value": [25.0],
                "unit": ["AUD/tCO2"],
            }
        )
        pack = {"assumptions": assumptions, "policy": policy}

        errors = validate_assumptions_pack(pack)

        assert len(errors) >= 1
        assert any("assumptions missing columns" in e for e in errors)

    def test_detects_missing_policy_columns(self) -> None:
        assumptions = pd.DataFrame(
            {
                "region": ["AUS"],
                "year": [2025],
                "param": ["capex"],
                "value": [1000.0],
                "unit": ["AUD/kW"],
                "uncertainty_band": ["mean"],
            }
        )
        policy = pd.DataFrame({"region": ["AUS"], "year": [2025], "unit": ["AUD/tCO2"]})
        pack = {"assumptions": assumptions, "policy": policy}

        errors = validate_assumptions_pack(pack)

        assert len(errors) >= 1
        assert any("policy missing columns" in e for e in errors)

    def test_detects_empty_unit_in_assumptions(self) -> None:
        assumptions = pd.DataFrame(
            {
                "region": ["AUS", "AUS"],
                "year": [2025, 2025],
                "param": ["capex", "opex"],
                "value": [1000.0, 10.0],
                "unit": ["AUD/kW", None],
                "uncertainty_band": ["mean", "mean"],
            }
        )
        policy = pd.DataFrame(
            {
                "region": ["AUS"],
                "year": [2025],
                "policy_type": ["carbon_price"],
                "value": [25.0],
                "unit": ["AUD/tCO2"],
            }
        )
        pack = {"assumptions": assumptions, "policy": policy}

        errors = validate_assumptions_pack(pack)

        assert any("assumptions table has empty unit values" in e for e in errors)

    def test_detects_empty_unit_in_policy(self) -> None:
        assumptions = pd.DataFrame(
            {
                "region": ["AUS"],
                "year": [2025],
                "param": ["capex"],
                "value": [1000.0],
                "unit": ["AUD/kW"],
                "uncertainty_band": ["mean"],
            }
        )
        policy = pd.DataFrame(
            {
                "region": ["AUS"],
                "year": [2025],
                "policy_type": ["carbon_price"],
                "value": [25.0],
                "unit": [None],
            }
        )
        pack = {"assumptions": assumptions, "policy": policy}

        errors = validate_assumptions_pack(pack)

        assert any("policy table has empty unit values" in e for e in errors)

    def test_multiple_errors_reported(self) -> None:
        assumptions = pd.DataFrame(
            {"region": ["AUS"], "year": [2025], "param": ["capex"], "unit": ["AUD/kW"]}
        )
        policy = pd.DataFrame({"region": ["AUS"], "year": [2025], "unit": ["AUD/tCO2"]})
        pack = {"assumptions": assumptions, "policy": policy}

        errors = validate_assumptions_pack(pack)

        assert len(errors) >= 2


class TestValidateScenarioPack:
    """Tests for validate_scenario_pack()."""

    def test_valid_pack_returns_empty_errors(self, tiny_scenario_pack: dict) -> None:
        errors = validate_scenario_pack(tiny_scenario_pack)
        assert errors == []

    def test_detects_missing_patch_columns(self) -> None:
        patches = pd.DataFrame(
            {
                "target": ["assumptions"],
                "region": ["AUS"],
                "operation": ["replace"],
                "unit": ["AUD/kW"],
            }
        )
        pack = {"patches": patches}

        errors = validate_scenario_pack(pack)

        assert len(errors) >= 1
        assert any("patches missing columns" in e for e in errors)

    def test_detects_invalid_operations(self) -> None:
        patches = pd.DataFrame(
            {
                "target": ["assumptions"],
                "region": ["AUS"],
                "year": [2025],
                "param": ["capex"],
                "operation": ["invalid_op"],
                "value": [1000.0],
                "unit": ["AUD/kW"],
                "rationale": ["Test"],
            }
        )
        pack = {"patches": patches}

        errors = validate_scenario_pack(pack)

        assert any("invalid operations" in e for e in errors)
        assert any("invalid_op" in e for e in errors)

    def test_detects_invalid_targets(self) -> None:
        patches = pd.DataFrame(
            {
                "target": ["invalid_target"],
                "region": ["AUS"],
                "year": [2025],
                "param": ["capex"],
                "operation": ["replace"],
                "value": [1000.0],
                "unit": ["AUD/kW"],
                "rationale": ["Test"],
            }
        )
        pack = {"patches": patches}

        errors = validate_scenario_pack(pack)

        assert any("invalid targets" in e for e in errors)
        assert any("invalid_target" in e for e in errors)

    def test_detects_empty_unit_in_patches(self) -> None:
        patches = pd.DataFrame(
            {
                "target": ["assumptions"],
                "region": ["AUS"],
                "year": [2025],
                "param": ["capex"],
                "operation": ["replace"],
                "value": [1000.0],
                "unit": [None],
                "rationale": ["Test"],
            }
        )
        pack = {"patches": patches}

        errors = validate_scenario_pack(pack)

        assert any("patches table has empty unit values" in e for e in errors)

    def test_multiple_invalid_operations(self) -> None:
        patches = pd.DataFrame(
            {
                "target": ["assumptions", "assumptions"],
                "region": ["AUS", "AUS"],
                "year": [2025, 2025],
                "param": ["capex", "opex"],
                "operation": ["bad_op1", "bad_op2"],
                "value": [1000.0, 10.0],
                "unit": ["AUD/kW", "AUD/kWh"],
                "rationale": ["Test1", "Test2"],
            }
        )
        pack = {"patches": patches}

        errors = validate_scenario_pack(pack)

        assert any("invalid operations" in e for e in errors)

    def test_allowed_operations_pass(self) -> None:
        patches = pd.DataFrame(
            {
                "target": ["assumptions", "assumptions", "policy"],
                "region": ["AUS", "AUS", "AUS"],
                "year": [2025, 2025, 2025],
                "param": ["capex", "opex", "carbon_price"],
                "operation": ["replace", "scale", "add"],
                "value": [1000.0, 0.9, 25.0],
                "unit": ["AUD/kW", "factor", "AUD/tCO2"],
                "rationale": ["Test1", "Test2", "Test3"],
            }
        )
        pack = {"patches": patches}

        errors = validate_scenario_pack(pack)

        assert not any("invalid operations" in e for e in errors)

    def test_allowed_targets_pass(self) -> None:
        patches = pd.DataFrame(
            {
                "target": ["assumptions", "policy"],
                "region": ["AUS", "AUS"],
                "year": [2025, 2025],
                "param": ["capex", "carbon_price"],
                "operation": ["replace", "replace"],
                "value": [1000.0, 25.0],
                "unit": ["AUD/kW", "AUD/tCO2"],
                "rationale": ["Test1", "Test2"],
            }
        )
        pack = {"patches": patches}

        errors = validate_scenario_pack(pack)

        assert not any("invalid targets" in e for e in errors)
