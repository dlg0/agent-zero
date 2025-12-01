"""Unit tests for the parse_years function in CLI."""

from __future__ import annotations

import pytest

from agent_zero.cli import parse_years


class TestParseYearsRange:
    """Tests for 'start:end' format."""

    def test_basic_range(self) -> None:
        """Test simple start:end range."""
        assert parse_years("2024:2030") == [2024, 2025, 2026, 2027, 2028, 2029, 2030]

    def test_single_year_range(self) -> None:
        """Test range where start equals end."""
        assert parse_years("2025:2025") == [2025]

    def test_range_with_whitespace(self) -> None:
        """Test range with leading/trailing whitespace."""
        assert parse_years("  2024:2026  ") == [2024, 2025, 2026]


class TestParseYearsRangeWithStep:
    """Tests for 'start:step:end' format."""

    def test_step_of_5(self) -> None:
        """Test range with step of 5."""
        assert parse_years("2024:5:2050") == [2024, 2029, 2034, 2039, 2044, 2049]

    def test_step_of_10(self) -> None:
        """Test range with step of 10."""
        assert parse_years("2020:10:2050") == [2020, 2030, 2040, 2050]

    def test_step_not_divisible(self) -> None:
        """Test range where step doesn't evenly divide the range."""
        assert parse_years("2020:3:2025") == [2020, 2023]

    def test_step_of_1(self) -> None:
        """Test explicit step of 1."""
        assert parse_years("2024:1:2027") == [2024, 2025, 2026, 2027]

    def test_step_larger_than_range(self) -> None:
        """Test step larger than range returns only start."""
        assert parse_years("2024:100:2030") == [2024]


class TestParseYearsList:
    """Tests for 'y1,y2,y3' format."""

    def test_basic_list(self) -> None:
        """Test comma-separated list."""
        result = parse_years("2024,2030,2040,2050")
        assert result == [2024, 2030, 2040, 2050]

    def test_list_sorted(self) -> None:
        """Test that list output is sorted."""
        result = parse_years("2050,2024,2035,2030")
        assert result == [2024, 2030, 2035, 2050]

    def test_single_item_list(self) -> None:
        """Test single-item list."""
        assert parse_years("2025") == [2025]

    def test_list_with_spaces(self) -> None:
        """Test list with spaces around values."""
        result = parse_years("2024, 2030, 2040")
        assert result == [2024, 2030, 2040]


class TestParseYearsErrors:
    """Tests for error handling."""

    def test_invalid_list_format(self) -> None:
        """Test invalid comma-separated values."""
        with pytest.raises(ValueError, match="Invalid year list format"):
            parse_years("2024,abc,2030")

    def test_invalid_range_format(self) -> None:
        """Test invalid range values."""
        with pytest.raises(ValueError, match="Invalid year range format"):
            parse_years("abc:2030")

    def test_invalid_step_format(self) -> None:
        """Test invalid step value."""
        with pytest.raises(ValueError, match="Invalid year range format"):
            parse_years("2024:abc:2050")

    def test_zero_step(self) -> None:
        """Test that step of 0 raises error."""
        with pytest.raises(ValueError, match="Step must be positive"):
            parse_years("2024:0:2050")

    def test_negative_step(self) -> None:
        """Test that negative step raises error."""
        with pytest.raises(ValueError, match="Step must be positive"):
            parse_years("2024:-1:2050")

    def test_start_greater_than_end(self) -> None:
        """Test that start > end raises error."""
        with pytest.raises(ValueError, match=r"Start year.*must be <= end year"):
            parse_years("2050:2024")

    def test_too_many_colons(self) -> None:
        """Test range with too many colons."""
        with pytest.raises(ValueError, match="Invalid year range format"):
            parse_years("2024:1:5:2050")

    def test_completely_invalid(self) -> None:
        """Test completely invalid input."""
        with pytest.raises(ValueError, match="Invalid year specification"):
            parse_years("invalid")
