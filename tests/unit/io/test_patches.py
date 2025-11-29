"""Unit tests for the apply_patches module.

Tests cover all patch operations (replace, scale, add), partial dimension
matching, targeting both assumptions and policy tables, and sequential
patch application.
"""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from agent_zero.io.apply_patches import DIM_COLS, apply_patches


@pytest.fixture
def sample_assumptions() -> pd.DataFrame:
    """Create a sample assumptions DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "region": "AUS",
                "sector": "energy",
                "tech": "solar",
                "year": 2025,
                "param": "capex",
                "value": 100.0,
                "unit": "USD/kW",
            },
            {
                "region": "AUS",
                "sector": "energy",
                "tech": "wind",
                "year": 2025,
                "param": "capex",
                "value": 150.0,
                "unit": "USD/kW",
            },
            {
                "region": "USA",
                "sector": "energy",
                "tech": "solar",
                "year": 2025,
                "param": "capex",
                "value": 120.0,
                "unit": "USD/kW",
            },
            {
                "region": "AUS",
                "sector": "energy",
                "tech": "solar",
                "year": 2030,
                "param": "capex",
                "value": 80.0,
                "unit": "USD/kW",
            },
            {
                "region": "AUS",
                "sector": "transport",
                "tech": "ev",
                "year": 2025,
                "param": "cost",
                "value": 50.0,
                "unit": "USD",
            },
        ]
    )


@pytest.fixture
def sample_policy() -> pd.DataFrame:
    """Create a sample policy DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "region": "AUS",
                "sector": "energy",
                "tech": None,
                "year": 2025,
                "param": "carbon_price",
                "value": 25.0,
                "unit": "USD/tCO2",
            },
            {
                "region": "USA",
                "sector": "energy",
                "tech": None,
                "year": 2025,
                "param": "carbon_price",
                "value": 30.0,
                "unit": "USD/tCO2",
            },
            {
                "region": "AUS",
                "sector": "energy",
                "tech": None,
                "year": 2030,
                "param": "carbon_price",
                "value": 50.0,
                "unit": "USD/tCO2",
            },
        ]
    )


class TestReplaceOperation:
    """Tests for the replace operation."""

    def test_replace_existing_row(self, sample_assumptions, sample_policy):
        """Replace operation updates value in matching row."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "replace",
                    "value": 90.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _new_policy = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        assert len(matched) == 1
        assert matched.iloc[0]["value"] == 90.0
        assert len(new_assum) == len(sample_assumptions)

    def test_replace_adds_new_row_when_no_match(self, sample_assumptions, sample_policy):
        """Replace operation adds new row when no matching row exists."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "hydrogen",
                    "year": 2025,
                    "param": "capex",
                    "operation": "replace",
                    "value": 200.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        assert len(new_assum) == len(sample_assumptions) + 1
        added = new_assum.query("tech == 'hydrogen'")
        assert len(added) == 1
        assert added.iloc[0]["value"] == 200.0
        assert added.iloc[0]["region"] == "AUS"
        assert added.iloc[0]["param"] == "capex"

    def test_replace_multiple_matching_rows(self, sample_assumptions, sample_policy):
        """Replace operation updates all matching rows."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": None,
                    "param": "capex",
                    "operation": "replace",
                    "value": 75.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and param == 'capex'")
        assert len(matched) == 2
        assert all(matched["value"] == 75.0)


class TestScaleOperation:
    """Tests for the scale operation."""

    def test_scale_matching_rows(self, sample_assumptions, sample_policy):
        """Scale operation multiplies values in matching rows."""
        original_value = sample_assumptions.query(
            "region == 'AUS' and tech == 'solar' and year == 2025"
        ).iloc[0]["value"]

        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "scale",
                    "value": 1.5,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        assert matched.iloc[0]["value"] == original_value * 1.5

    def test_scale_with_zero(self, sample_assumptions, sample_policy):
        """Scale operation with zero multiplier sets value to zero."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "scale",
                    "value": 0.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        assert matched.iloc[0]["value"] == 0.0

    def test_scale_multiple_matching_rows(self, sample_assumptions, sample_policy):
        """Scale operation scales all matching rows."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": None,
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "scale",
                    "value": 2.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        aus_solar = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        usa_solar = new_assum.query("region == 'USA' and tech == 'solar' and year == 2025")
        assert aus_solar.iloc[0]["value"] == 200.0  # 100 * 2
        assert usa_solar.iloc[0]["value"] == 240.0  # 120 * 2


class TestAddOperation:
    """Tests for the add operation."""

    def test_add_to_matching_rows(self, sample_assumptions, sample_policy):
        """Add operation adds to values in matching rows."""
        original_value = sample_assumptions.query(
            "region == 'AUS' and tech == 'solar' and year == 2025"
        ).iloc[0]["value"]

        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "add",
                    "value": 10.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        assert matched.iloc[0]["value"] == original_value + 10.0

    def test_add_negative_value(self, sample_assumptions, sample_policy):
        """Add operation with negative value decreases the value."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "add",
                    "value": -20.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        assert matched.iloc[0]["value"] == 80.0  # 100 - 20

    def test_add_to_multiple_matching_rows(self, sample_assumptions, sample_policy):
        """Add operation adds to all matching rows."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": None,
                    "param": "capex",
                    "operation": "add",
                    "value": 5.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched_2025 = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        matched_2030 = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2030")
        assert matched_2025.iloc[0]["value"] == 105.0  # 100 + 5
        assert matched_2030.iloc[0]["value"] == 85.0  # 80 + 5


class TestPartialDimensionMatches:
    """Tests for patches with partial dimension matches (some dimensions are None)."""

    def test_none_region_matches_all_regions(self, sample_assumptions, sample_policy):
        """Patch with None region matches all regions."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": None,
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "scale",
                    "value": 0.5,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        aus = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        usa = new_assum.query("region == 'USA' and tech == 'solar' and year == 2025")
        assert aus.iloc[0]["value"] == 50.0  # 100 * 0.5
        assert usa.iloc[0]["value"] == 60.0  # 120 * 0.5

    def test_none_year_matches_all_years(self, sample_assumptions, sample_policy):
        """Patch with None year matches all years."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": None,
                    "param": "capex",
                    "operation": "replace",
                    "value": 60.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and param == 'capex'")
        assert len(matched) == 2
        assert all(matched["value"] == 60.0)

    def test_multiple_none_dimensions(self, sample_assumptions, sample_policy):
        """Patch with multiple None dimensions matches broadly."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": None,
                    "sector": None,
                    "tech": None,
                    "year": 2025,
                    "param": None,
                    "operation": "scale",
                    "value": 2.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        rows_2025 = new_assum.query("year == 2025")
        assert len(rows_2025) == 4
        assert all(rows_2025["value"] == sample_assumptions.query("year == 2025")["value"] * 2)

    def test_all_none_dimensions_matches_all_rows(self, sample_assumptions, sample_policy):
        """Patch with all None dimensions matches all rows."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": None,
                    "sector": None,
                    "tech": None,
                    "year": None,
                    "param": None,
                    "operation": "scale",
                    "value": 0.1,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        expected_values = sample_assumptions["value"] * 0.1
        assert list(new_assum["value"]) == list(expected_values)


class TestTargetTables:
    """Tests for patches targeting both assumptions and policy tables."""

    def test_patch_targets_policy_table(self, sample_assumptions, sample_policy):
        """Patch targeting policy table modifies only policy."""
        patches = pd.DataFrame(
            [
                {
                    "target": "policy",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": None,
                    "year": 2025,
                    "param": "carbon_price",
                    "operation": "replace",
                    "value": 35.0,
                    "unit": "USD/tCO2",
                }
            ]
        )

        new_assum, new_policy = apply_patches(sample_assumptions, sample_policy, patches)

        assert_frame_equal(
            new_assum[sample_assumptions.columns],
            sample_assumptions,
            check_dtype=False,
        )
        matched = new_policy.query("region == 'AUS' and year == 2025")
        assert matched.iloc[0]["value"] == 35.0

    def test_patch_targets_assumptions_table(self, sample_assumptions, sample_policy):
        """Patch targeting assumptions table modifies only assumptions."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "replace",
                    "value": 95.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, new_policy = apply_patches(sample_assumptions, sample_policy, patches)

        assert_frame_equal(
            new_policy[sample_policy.columns],
            sample_policy,
            check_dtype=False,
        )
        matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        assert matched.iloc[0]["value"] == 95.0

    def test_scale_policy_table(self, sample_assumptions, sample_policy):
        """Scale operation works on policy table."""
        patches = pd.DataFrame(
            [
                {
                    "target": "policy",
                    "region": None,
                    "sector": "energy",
                    "tech": None,
                    "year": None,
                    "param": "carbon_price",
                    "operation": "scale",
                    "value": 1.2,
                    "unit": "USD/tCO2",
                }
            ]
        )

        _, new_policy = apply_patches(sample_assumptions, sample_policy, patches)

        assert (
            new_policy.query("region == 'AUS' and year == 2025").iloc[0]["value"] == 30.0
        )  # 25 * 1.2
        assert (
            new_policy.query("region == 'USA' and year == 2025").iloc[0]["value"] == 36.0
        )  # 30 * 1.2
        assert (
            new_policy.query("region == 'AUS' and year == 2030").iloc[0]["value"] == 60.0
        )  # 50 * 1.2

    def test_add_to_policy_table(self, sample_assumptions, sample_policy):
        """Add operation works on policy table."""
        patches = pd.DataFrame(
            [
                {
                    "target": "policy",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": None,
                    "year": 2025,
                    "param": "carbon_price",
                    "operation": "add",
                    "value": 5.0,
                    "unit": "USD/tCO2",
                }
            ]
        )

        _, new_policy = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_policy.query("region == 'AUS' and year == 2025")
        assert matched.iloc[0]["value"] == 30.0  # 25 + 5


class TestMultiplePatches:
    """Tests for multiple patches applied in sequence."""

    def test_multiple_patches_in_sequence(self, sample_assumptions, sample_policy):
        """Multiple patches are applied in order."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "replace",
                    "value": 90.0,
                    "unit": "USD/kW",
                },
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "scale",
                    "value": 2.0,
                    "unit": "USD/kW",
                },
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        assert matched.iloc[0]["value"] == 180.0  # 90 * 2

    def test_patches_to_both_tables(self, sample_assumptions, sample_policy):
        """Patches can target both tables in same call."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "add",
                    "value": 50.0,
                    "unit": "USD/kW",
                },
                {
                    "target": "policy",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": None,
                    "year": 2025,
                    "param": "carbon_price",
                    "operation": "add",
                    "value": 10.0,
                    "unit": "USD/tCO2",
                },
            ]
        )

        new_assum, new_policy = apply_patches(sample_assumptions, sample_policy, patches)

        assum_matched = new_assum.query("region == 'AUS' and tech == 'solar' and year == 2025")
        policy_matched = new_policy.query("region == 'AUS' and year == 2025")
        assert assum_matched.iloc[0]["value"] == 150.0  # 100 + 50
        assert policy_matched.iloc[0]["value"] == 35.0  # 25 + 10

    def test_replace_then_add_sequence(self, sample_assumptions, sample_policy):
        """Replace followed by add is applied correctly."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "wind",
                    "year": 2025,
                    "param": "capex",
                    "operation": "replace",
                    "value": 100.0,
                    "unit": "USD/kW",
                },
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "wind",
                    "year": 2025,
                    "param": "capex",
                    "operation": "add",
                    "value": 25.0,
                    "unit": "USD/kW",
                },
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("region == 'AUS' and tech == 'wind' and year == 2025")
        assert matched.iloc[0]["value"] == 125.0  # 100 + 25

    def test_add_new_row_then_modify(self, sample_assumptions, sample_policy):
        """New row added by replace can be modified by subsequent patch."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "hydrogen",
                    "year": 2025,
                    "param": "capex",
                    "operation": "replace",
                    "value": 300.0,
                    "unit": "USD/kW",
                },
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "hydrogen",
                    "year": 2025,
                    "param": "capex",
                    "operation": "scale",
                    "value": 0.5,
                    "unit": "USD/kW",
                },
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        matched = new_assum.query("tech == 'hydrogen'")
        assert len(matched) == 1
        assert matched.iloc[0]["value"] == 150.0  # 300 * 0.5


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_patches(self, sample_assumptions, sample_policy):
        """Empty patches DataFrame returns unchanged tables."""
        patches = pd.DataFrame(
            columns=[
                "target",
                "region",
                "sector",
                "tech",
                "year",
                "param",
                "operation",
                "value",
                "unit",
            ]
        )

        new_assum, new_policy = apply_patches(sample_assumptions, sample_policy, patches)

        assert_frame_equal(
            new_assum[sample_assumptions.columns],
            sample_assumptions,
            check_dtype=False,
        )
        assert_frame_equal(
            new_policy[sample_policy.columns],
            sample_policy,
            check_dtype=False,
        )

    def test_no_matching_rows_for_scale(self, sample_assumptions, sample_policy):
        """Scale on non-matching rows has no effect."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "NONEXISTENT",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "scale",
                    "value": 2.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        assert_frame_equal(
            new_assum[sample_assumptions.columns],
            sample_assumptions,
            check_dtype=False,
        )

    def test_no_matching_rows_for_add(self, sample_assumptions, sample_policy):
        """Add on non-matching rows has no effect."""
        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "NONEXISTENT",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "add",
                    "value": 10.0,
                    "unit": "USD/kW",
                }
            ]
        )

        new_assum, _ = apply_patches(sample_assumptions, sample_policy, patches)

        assert_frame_equal(
            new_assum[sample_assumptions.columns],
            sample_assumptions,
            check_dtype=False,
        )

    def test_original_dataframes_not_modified(self, sample_assumptions, sample_policy):
        """Original DataFrames are not modified by apply_patches."""
        original_assum = sample_assumptions.copy()
        original_policy = sample_policy.copy()

        patches = pd.DataFrame(
            [
                {
                    "target": "assumptions",
                    "region": "AUS",
                    "sector": "energy",
                    "tech": "solar",
                    "year": 2025,
                    "param": "capex",
                    "operation": "replace",
                    "value": 999.0,
                    "unit": "USD/kW",
                }
            ]
        )

        apply_patches(sample_assumptions, sample_policy, patches)

        assert_frame_equal(sample_assumptions, original_assum)
        assert_frame_equal(sample_policy, original_policy)

    def test_dim_cols_constant(self):
        """DIM_COLS contains expected dimension columns."""
        expected = ["region", "sector", "tech", "year", "param"]
        assert expected == DIM_COLS
