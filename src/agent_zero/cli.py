"""Command‑line interface for AgentZero.

This module provides a `click` based CLI with commands to validate
assumptions and scenario packs, build resolved assumptions, run
simulations and list completed runs.
"""

from __future__ import annotations

import json
from pathlib import Path
import click

from .io.load_pack import load_assumptions_pack, load_scenario_pack, load_manifest
from .io.validate import validate_assumptions_pack, validate_scenario_pack
from .io.apply_patches import apply_patches
from .io.hashing import make_run_id
from .model.world import init_world
from .model.agents import init_agents
from .model.simulate import simulate
from .post.results_pack import write_run_bundle

# Bump this when the engine changes in incompatible ways
ENGINE_VERSION = "0.1.0"


@click.group()
def main() -> None:
    """AgentZero command line interface."""
    pass


@main.command()
@click.argument("pack_path")
def validate(pack_path: str) -> None:
    """Validate an assumptions or scenario pack.

    PACK_PATH should point at the directory containing the pack's
    manifest.yaml. The command prints 'OK' on success and otherwise
    lists validation errors before exiting with code 1.
    """
    p = Path(pack_path)
    manifest = load_manifest(p)
    pack_type = manifest.get("type")

    if pack_type == "assumptions":
        pack = load_assumptions_pack(p)
        errs = validate_assumptions_pack(pack)
    elif pack_type == "scenario":
        pack = load_scenario_pack(p)
        errs = validate_scenario_pack(pack)
    else:
        raise click.ClickException(
            f"Unknown pack type '{pack_type}' in manifest.yaml; "
            "expected 'assumptions' or 'scenario'."
        )
    if errs:
        for e in errs:
            click.echo(f"ERROR: {e}")
        raise SystemExit(1)
    click.echo("OK")


@main.command()
@click.option("--assum", required=True, help="Assumptions pack name under data/assumptions_packs")
@click.option("--scen", required=False, help="Scenario pack name under data/scenario_packs")
@click.option("--out", required=True, help="Output Parquet file path for resolved assumptions table")
def build(assum: str, scen: str | None, out: str) -> None:
    """Build a resolved assumptions table from a baseline and scenario.

    This command applies scenario patches to the baseline assumptions and
    policy tables and writes the resolved assumptions table to OUT.
    """
    ap_path = Path("data/assumptions_packs") / assum
    ap = load_assumptions_pack(ap_path)
    assumptions = ap["assumptions"]
    policy = ap["policy"]

    if scen:
        sp_path = Path("data/scenario_packs") / scen
        sp = load_scenario_pack(sp_path)
        assumptions, policy = apply_patches(assumptions, policy, sp["patches"])

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    # Write only the assumptions table; policy modifications can be inspected in run outputs
    assumptions.to_parquet(out, index=False)
    click.echo(f"Wrote resolved assumptions to {out}")


@main.command()
@click.option("--assum", required=True, help="Assumptions pack name under data/assumptions_packs")
@click.option("--scen", required=False, help="Scenario pack name under data/scenario_packs")
@click.option("--years", required=True, help="Year range in the format start:end (inclusive)")
@click.option("--seed", default=0, type=int, help="Random seed (unused in v1 but reserved)")
@click.option("--out", default="runs/", help="Output directory to write the run bundle")
def run(assum: str, scen: str | None, years: str, seed: int, out: str) -> None:
    """Run a simulation with a baseline and optional scenario.

    The YEAR range should be in the form 'YYYY:YYYY'. The output
    directory will be created if it does not exist.
    """
    # parse years range
    try:
        start_year, end_year = [int(x) for x in years.split(":")]
    except Exception as e:
        raise click.BadParameter("--years must be in the format start:end") from e

    year_list = list(range(start_year, end_year + 1))

    # load baseline
    ap_path = Path("data/assumptions_packs") / assum
    ap = load_assumptions_pack(ap_path)
    assumptions = ap["assumptions"]
    policy = ap["policy"]
    sp = None
    # apply scenario if provided
    if scen:
        sp_path = Path("data/scenario_packs") / scen
        sp = load_scenario_pack(sp_path)
        assumptions, policy = apply_patches(assumptions, policy, sp["patches"])

    # initialise world and agents
    world0 = init_world(assumptions, policy, start_year=start_year)
    agents0 = init_agents(assumptions, start_year=start_year)

    # run simulation
    history = simulate(world0, agents0, years=year_list)

    # produce run ID
    run_id = make_run_id(
        ENGINE_VERSION,
        ap["manifest"].get("hash", "NA"),
        sp["manifest"].get("hash", "NA") if sp else None,
        years=year_list,
        seed=seed
    )

    manifests = {
        "assumptions": ap["manifest"],
        "scenario": sp["manifest"] if sp else {},
    }
    out_dir = write_run_bundle(Path(out), run_id, history, manifests)
    click.echo(f"Run complete: {out_dir}")


@main.command()
def runs() -> None:
    """List all previously executed runs."""
    rdir = Path("runs")
    if not rdir.exists():
        click.echo("No runs/ directory yet.")
        return
    for p in sorted(rdir.iterdir()):
        if p.is_dir():
            click.echo(p.name)