"""Shared pytest fixtures for agent-zero tests.

This module provides centralized fixtures for:
- Path management (repo root, data directories)
- Loading production and test data packs
- Pre-initialized world and agent states
- Synthetic in-memory test data for fast unit tests
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agent_zero.io.load_pack import load_assumptions_pack, load_scenario_pack
from agent_zero.model.agents import init_agents
from agent_zero.model.world import init_world
from agent_zero.utils.types import AgentState, WorldState

# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def data_dir(repo_root: Path) -> Path:
    """Return the production data directory."""
    return repo_root / "data"


@pytest.fixture
def test_data_dir() -> Path:
    """Return the test data directory for synthetic fixtures."""
    return Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Production pack fixtures (for integration tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def baseline_pack(data_dir: Path) -> dict:
    """Load the baseline-v1 assumptions pack."""
    pack_dir = data_dir / "assumptions_packs" / "baseline-v1"
    return load_assumptions_pack(pack_dir)


@pytest.fixture
def fast_elec_pack(data_dir: Path) -> dict:
    """Load the fast-elec-v1 scenario pack."""
    scen_dir = data_dir / "scenario_packs" / "fast-elec-v1"
    return load_scenario_pack(scen_dir)


@pytest.fixture
def baseline_world_agents(baseline_pack: dict) -> tuple[WorldState, list[AgentState]]:
    """Initialize world and agents from the baseline pack."""
    assumptions = baseline_pack["assumptions"]
    policy = baseline_pack["policy"]
    start_year = 2025
    world0 = init_world(assumptions, policy, start_year=start_year)
    agents0 = init_agents(assumptions, start_year=start_year)
    return world0, agents0


# ---------------------------------------------------------------------------
# Synthetic test data fixtures (for fast unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def tiny_assumptions() -> pd.DataFrame:
    """Create minimal synthetic assumptions DataFrame."""
    return pd.DataFrame(
        [
            {
                "region": "AUS",
                "sector": None,
                "tech": "electricity",
                "year": 2025,
                "param": "capex",
                "value": 1000.0,
                "unit": "AUD/kW",
                "uncertainty_band": "mean",
            },
            {
                "region": "AUS",
                "sector": None,
                "tech": "electricity",
                "year": 2025,
                "param": "demand",
                "value": 100.0,
                "unit": "MW",
                "uncertainty_band": "mean",
            },
            {
                "region": "AUS",
                "sector": None,
                "tech": "hydrogen",
                "year": 2025,
                "param": "capex",
                "value": 800.0,
                "unit": "AUD/kW",
                "uncertainty_band": "mean",
            },
            {
                "region": "AUS",
                "sector": None,
                "tech": "hydrogen",
                "year": 2025,
                "param": "demand",
                "value": 10.0,
                "unit": "MW",
                "uncertainty_band": "mean",
            },
        ]
    )


@pytest.fixture
def tiny_policy() -> pd.DataFrame:
    """Create minimal synthetic policy DataFrame."""
    return pd.DataFrame(
        [
            {
                "region": "AUS",
                "sector": None,
                "year": 2025,
                "policy_type": "carbon_price",
                "value": 0.0,
                "unit": "AUD/tCO2",
            },
            {
                "region": "AUS",
                "sector": None,
                "year": 2026,
                "policy_type": "carbon_price",
                "value": 25.0,
                "unit": "AUD/tCO2",
            },
        ]
    )


@pytest.fixture
def tiny_patches() -> pd.DataFrame:
    """Create minimal synthetic patches DataFrame."""
    return pd.DataFrame(
        [
            {
                "target": "assumptions",
                "region": "AUS",
                "sector": None,
                "tech": "electricity",
                "year": 2025,
                "param": "capex",
                "operation": "scale",
                "value": 0.9,
                "unit": "AUD/kW",
                "rationale": "Test scale",
            },
            {
                "target": "policy",
                "region": "AUS",
                "sector": None,
                "tech": None,
                "year": 2025,
                "param": "carbon_price",
                "operation": "replace",
                "value": 50.0,
                "unit": "AUD/tCO2",
                "rationale": "Test replace",
            },
        ]
    )


@pytest.fixture
def tiny_world(tiny_assumptions: pd.DataFrame, tiny_policy: pd.DataFrame) -> WorldState:
    """Create a minimal world state for unit testing."""
    return init_world(tiny_assumptions, tiny_policy, start_year=2025)


@pytest.fixture
def tiny_agents(tiny_assumptions: pd.DataFrame) -> list[AgentState]:
    """Create minimal agents for unit testing."""
    return init_agents(tiny_assumptions, start_year=2025)


# ---------------------------------------------------------------------------
# Test pack fixtures (for loading from tests/data/)
# ---------------------------------------------------------------------------


@pytest.fixture
def tiny_baseline_pack(test_data_dir: Path) -> dict:
    """Load the tiny-baseline test assumptions pack."""
    pack_dir = test_data_dir / "assumptions_packs" / "tiny-baseline"
    return load_assumptions_pack(pack_dir)


@pytest.fixture
def tiny_scenario_pack(test_data_dir: Path) -> dict:
    """Load the tiny-scenario test scenario pack."""
    scen_dir = test_data_dir / "scenario_packs" / "tiny-scenario"
    return load_scenario_pack(scen_dir)
