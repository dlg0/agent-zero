"""Tests for pack validation functions."""

from pathlib import Path
from agent_zero.io.load_pack import load_assumptions_pack, load_scenario_pack
from agent_zero.io.validate import validate_assumptions_pack, validate_scenario_pack


def test_validate_baseline_ok():
    pack_dir = Path('data/assumptions_packs/baseline-v1')
    pack = load_assumptions_pack(pack_dir)
    errs = validate_assumptions_pack(pack)
    assert errs == []


def test_validate_scenario_ok():
    scen_dir = Path('data/scenario_packs/fast-elec-v1')
    pack = load_scenario_pack(scen_dir)
    errs = validate_scenario_pack(pack)
    assert errs == []
