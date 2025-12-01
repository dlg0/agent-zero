"""Command‑line interface for AgentZero.

This module provides a `click` based CLI with commands to validate
assumptions and scenario packs, build resolved assumptions, run
simulations and list completed runs.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import rich_click as click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .io.apply_patches import apply_patches
from .io.hashing import make_run_id
from .io.load_pack import load_assumptions_pack, load_manifest, load_scenario_pack
from .io.validate import validate_assumptions_pack, validate_scenario_pack
from .model.agents import init_agents
from .model.simulate import simulate
from .model.world import init_world
from .post.export_web import export_web_bundle, rebuild_web_index
from .post.results_pack import write_run_bundle
from .post.results_validation import validate_bundle

try:
    from .story.generator import StoryGenerator, StoryOutput

    STORY_AVAILABLE = True
except ImportError:
    STORY_AVAILABLE = False
    StoryGenerator = None  # type: ignore[misc, assignment]
    StoryOutput = None  # type: ignore[misc, assignment]

ENGINE_VERSION = "0.1.0"

console = Console()


def echo_info(msg: str) -> None:
    console.print(f"[cyan]ℹ[/] {msg}")


def echo_success(msg: str) -> None:
    console.print(f"[green]✓[/] {msg}")


def echo_warning(msg: str) -> None:
    console.print(f"[yellow]⚠[/] {msg}")


def echo_error(msg: str) -> None:
    console.print(f"[bold red]✗[/] {msg}")


def echo_step(msg: str) -> None:
    console.print(f"  [dim]→[/] {msg}")


def parse_years(years_str: str) -> list[int]:
    """Parse a year specification string into a list of years.

    Supported formats:
    - "2024:2050" - range from 2024 to 2050 inclusive (step 1)
    - "2024:5:2050" - range from 2024 to 2050 inclusive with step 5
    - "2024,2030,2040,2050" - explicit comma-separated list

    Args:
        years_str: The year specification string

    Returns:
        A sorted list of years

    Raises:
        ValueError: If the format is invalid
    """
    years_str = years_str.strip()

    if "," in years_str:
        try:
            year_list = [int(y.strip()) for y in years_str.split(",")]
            return sorted(year_list)
        except ValueError as e:
            raise ValueError(
                f"Invalid year list format: '{years_str}'. "
                "Expected comma-separated integers like '2024,2030,2040'"
            ) from e

    if ":" in years_str:
        parts = years_str.split(":")
        if len(parts) == 2:
            try:
                start, end = int(parts[0]), int(parts[1])
                step = 1
            except ValueError as e:
                raise ValueError(
                    f"Invalid year range format: '{years_str}'. "
                    "Expected 'start:end' like '2024:2050'"
                ) from e
        elif len(parts) == 3:
            try:
                start, step, end = int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError as e:
                raise ValueError(
                    f"Invalid year range format: '{years_str}'. "
                    "Expected 'start:step:end' like '2024:5:2050'"
                ) from e
            if step <= 0:
                raise ValueError(f"Step must be positive, got {step}")
        else:
            raise ValueError(
                f"Invalid year range format: '{years_str}'. "
                "Expected 'start:end' or 'start:step:end'"
            )

        if start > end:
            raise ValueError(f"Start year ({start}) must be <= end year ({end})")

        return list(range(start, end + 1, step))

    try:
        return [int(years_str)]
    except ValueError as e:
        raise ValueError(
            f"Invalid year specification: '{years_str}'. "
            "Expected 'start:end', 'start:step:end', 'year1,year2,...', or single year"
        ) from e


WORKFLOW_HELP = """
[bold cyan]AgentZero[/] - Agent-based simulation framework

[bold]TYPICAL WORKFLOW[/]

  [cyan]1.[/] [bold]VALIDATE[/] your data packs (optional but recommended):
     $ agentzero validate-inputs data/assumptions_packs/baseline
     $ agentzero validate-inputs data/scenario_packs/high_growth

  [cyan]2.[/] [bold]BUILD[/] a resolved assumptions table (optional, for inspection):
     $ agentzero build --assum baseline --out resolved.parquet
     $ agentzero build --assum baseline --scen high_growth --out resolved.parquet

  [cyan]3.[/] [bold]RUN[/] a simulation:
     $ agentzero run --assum baseline --years 2024:2050
     $ agentzero run --assum baseline --years 2024:5:2050  (every 5 years)
     $ agentzero run --assum baseline --years 2024,2030,2040,2050

  [cyan]4.[/] [bold]LIST[/] previous runs:
     $ agentzero runs

[bold]DATA STRUCTURE[/]
  data/
    assumptions_packs/   ← Baseline assumptions (required)
      baseline/
        manifest.yaml
        assumptions.csv
        policy.csv
    scenario_packs/      ← Scenario patches (optional)
      high_growth/
        manifest.yaml
        patches.yaml

For more details on each command, use: [bold]agentzero <command> --help[/]
"""


def print_banner() -> None:
    banner = Text()
    banner.append("AgentZero", style="bold cyan")
    banner.append(" v" + ENGINE_VERSION, style="dim")
    console.print(banner)


@click.group(invoke_without_command=True)
@click.version_option(version=ENGINE_VERSION, prog_name="agentzero")
@click.pass_context
def main(ctx: click.Context) -> None:
    """AgentZero: Run agent-based simulations with assumptions and scenarios."""
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print()
        console.print(WORKFLOW_HELP)


@main.command("validate-inputs")
@click.argument("pack_path")
def validate_inputs(pack_path: str) -> None:
    """Validate an assumptions or scenario pack.

    PACK_PATH should point at the directory containing the pack's
    manifest.yaml. The command prints 'OK' on success and otherwise
    lists validation errors before exiting with code 1.
    """
    console.rule("[bold cyan]Validating Pack[/]")

    p = Path(pack_path)
    echo_info(f"Reading manifest from [dim]{p}[/]")
    manifest = load_manifest(p)
    pack_type = manifest.get("type")

    if pack_type == "assumptions":
        echo_info("Detected [bold]assumptions[/] pack")
        pack = load_assumptions_pack(p)
        errs = validate_assumptions_pack(pack)
    elif pack_type == "scenario":
        echo_info("Detected [bold]scenario[/] pack")
        pack = load_scenario_pack(p)
        errs = validate_scenario_pack(pack)
    else:
        raise click.ClickException(
            f"Unknown pack type '{pack_type}' in manifest.yaml; "
            "expected 'assumptions' or 'scenario'."
        )

    if errs:
        console.print()
        echo_error("Validation failed:")
        for e in errs:
            console.print(f"  [red]•[/] {e}")
        raise SystemExit(1)

    console.print()
    echo_success("Pack is valid")


@main.command()
@click.option("--assum", required=True, help="Assumptions pack name under data/assumptions_packs")
@click.option("--scen", required=False, help="Scenario pack name under data/scenario_packs")
@click.option(
    "--out", required=True, help="Output Parquet file path for resolved assumptions table"
)
def build(assum: str, scen: str | None, out: str) -> None:
    """Build a resolved assumptions table from a baseline and scenario.

    This command applies scenario patches to the baseline assumptions and
    policy tables and writes the resolved assumptions table to OUT.
    """
    console.rule("[bold cyan]Building Resolved Assumptions[/]")

    echo_info(f"Baseline: [bold cyan]{assum}[/]")
    if scen:
        echo_info(f"Scenario: [bold cyan]{scen}[/]")
    else:
        echo_info("Scenario: [dim](none)[/]")

    ap_path = Path("data/assumptions_packs") / assum
    echo_step("Loading assumptions pack...")
    ap = load_assumptions_pack(ap_path)
    assumptions = ap["assumptions"]
    policy = ap["policy"]

    if scen:
        sp_path = Path("data/scenario_packs") / scen
        echo_step(f"Applying scenario patches from [dim]{sp_path}[/]")
        sp = load_scenario_pack(sp_path)
        assumptions, policy = apply_patches(assumptions, policy, sp["patches"])

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    assumptions.to_parquet(out, index=False)

    console.print()
    echo_success(f"Wrote resolved assumptions to [bold green]{out}[/]")


@main.command()
@click.option("--assum", required=True, help="Assumptions pack name under data/assumptions_packs")
@click.option("--scen", required=False, help="Scenario pack name under data/scenario_packs")
@click.option(
    "--years",
    required=True,
    help="Year specification: 'start:end', 'start:step:end', or 'y1,y2,y3,...'",
)
@click.option("--seed", default=0, type=int, help="Random seed (unused in v1 but reserved)")
@click.option("--out", default="runs/", help="Output directory to write the run bundle")
def run(assum: str, scen: str | None, years: str, seed: int, out: str) -> None:
    """Run a simulation with a baseline and optional scenario.

    Year specification formats:
    \b
    - "2024:2050" - range from 2024 to 2050 (step 1)
    - "2024:5:2050" - range from 2024 to 2050 (step 5)
    - "2024,2030,2040,2050" - explicit comma-separated list

    The output directory will be created if it does not exist.
    """
    cli_command = " ".join(shlex.quote(arg) for arg in sys.argv)

    console.rule("[bold cyan]Running Simulation[/]")

    try:
        year_list = parse_years(years)
    except ValueError as e:
        raise click.BadParameter(str(e)) from e

    start_year = min(year_list)
    end_year = max(year_list)

    if len(year_list) == 1:
        echo_info(f"Year: [bold cyan]{year_list[0]}[/]")
    elif len(year_list) <= 10:
        years_str = ", ".join(str(y) for y in year_list)
        echo_info(f"Years: [bold cyan]{years_str}[/]")
    else:
        echo_info(
            f"Years: [bold cyan]{start_year}[/]–[bold cyan]{end_year}[/] ({len(year_list)} years)"
        )
    echo_info(f"Seed: [dim]{seed}[/]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Loading input data...", total=None)

        ap_path = Path("data/assumptions_packs") / assum
        ap = load_assumptions_pack(ap_path)
        assumptions = ap["assumptions"]
        policy = ap["policy"]
        sp = None

        if scen:
            progress.update(task, description="Applying scenario patches...")
            sp_path = Path("data/scenario_packs") / scen
            sp = load_scenario_pack(sp_path)
            assumptions, policy = apply_patches(assumptions, policy, sp["patches"])

        progress.update(task, description="Initializing world and agents...")
        world0 = init_world(assumptions, policy, start_year=start_year)
        agents0 = init_agents(assumptions, start_year=start_year)

        progress.update(task, description="Running simulation...")
        history = simulate(world0, agents0, years=year_list)

        progress.update(task, description="Writing run bundle...")
        run_id = make_run_id(
            ENGINE_VERSION,
            ap["manifest"].get("hash", "NA"),
            sp["manifest"].get("hash", "NA") if sp else None,
            years=year_list,
            seed=seed,
        )

        manifests = {
            "assumptions": ap["manifest"],
            "scenario": sp["manifest"] if sp else {},
        }
        out_dir = write_run_bundle(
            Path(out), run_id, history, manifests, seed=seed, cli_command=cli_command
        )

    panel_text = Text()
    panel_text.append("Run ID: ", style="bold")
    panel_text.append(f"{run_id}\n", style="cyan")
    panel_text.append("Output: ", style="bold")
    panel_text.append(f"{out_dir}\n", style="green")
    panel_text.append("Years:  ", style="bold")
    panel_text.append(f"{start_year}–{end_year}\n")
    panel_text.append("Seed:   ", style="bold")
    panel_text.append(str(seed))

    console.print(Panel(panel_text, title="[green]✓ Run Complete[/]", expand=False))


@main.command()
def runs() -> None:
    """List all previously executed runs."""
    rdir = Path("runs")
    if not rdir.exists():
        echo_warning("No runs directory found ([dim]runs/[/]).")
        return

    run_dirs = [p for p in sorted(rdir.iterdir()) if p.is_dir()]
    if not run_dirs:
        echo_warning("No runs found in [dim]runs/[/].")
        return

    table = Table(title="[bold cyan]Available Runs[/]", show_header=True, header_style="bold")
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Years", style="magenta")
    table.add_column("Assumptions", style="green")
    table.add_column("Scenario", style="yellow")

    for rd in run_dirs:
        manifest_path = rd / "manifest.yaml"
        years_str = "-"
        assum_name = "-"
        scen_name = "-"

        if manifest_path.exists():
            with manifest_path.open() as f:
                m = yaml.safe_load(f)
            years_info = m.get("years", {})
            if isinstance(years_info, dict):
                start = years_info.get("start", "?")
                end = years_info.get("end", "?")
                years_str = f"{start}–{end}"
            assum_info = m.get("assumptions", {})
            if isinstance(assum_info, dict):
                assum_name = assum_info.get("name", "-")
            scen_info = m.get("scenario", {})
            if isinstance(scen_info, dict):
                scen_name = scen_info.get("name", "-") if scen_info else "-"

        table.add_row(rd.name, years_str, assum_name, scen_name)

    console.print(table)


@main.command("validate-outputs")
@click.argument("run_dir", type=click.Path(exists=True, path_type=Path))
def validate_outputs(run_dir: Path) -> None:
    """Validate a results bundle for schema compliance.

    RUN_DIR is the path to a results bundle directory containing
    timeseries.parquet, agent_states.parquet, summary.json, and manifest.yaml.
    """
    console.rule("[bold cyan]Validating Results Bundle[/]")
    echo_info(f"Bundle: [dim]{run_dir}[/]")

    issues = validate_bundle(run_dir)

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    if not issues:
        console.print()
        echo_success(f"{run_dir}: Valid results bundle")
        raise SystemExit(0)

    console.print()
    for issue in issues:
        icon = "[bold red]✗[/]" if issue.level == "error" else "[yellow]⚠[/]"
        location = f"[dim]{issue.location}[/]"
        console.print(f"{icon} [{location}] {issue.message}")

    console.print()
    err_count = f"[bold red]{len(errors)} error(s)[/]"
    warn_count = f"[yellow]{len(warnings)} warning(s)[/]"
    console.print(f"Summary: {err_count}, {warn_count}")

    raise SystemExit(1 if errors else 0)


def _get_run_info(run_dir: Path) -> dict:
    """Extract useful info from a run's manifest for display."""
    manifest_path = run_dir / "manifest.yaml"
    info = {
        "run_id": run_dir.name,
        "years": "-",
        "assumptions": "-",
        "scenario": "-",
        "timestamp": "-",
    }
    if manifest_path.exists():
        with manifest_path.open() as f:
            m = yaml.safe_load(f)
        years_info = m.get("years", {})
        if isinstance(years_info, list) and years_info:
            info["years"] = f"{min(years_info)}–{max(years_info)}"
        elif isinstance(years_info, dict):
            start = years_info.get("start", "?")
            end = years_info.get("end", "?")
            info["years"] = f"{start}–{end}"
        assum_info = m.get("assumptions", {})
        if isinstance(assum_info, dict):
            info["assumptions"] = assum_info.get("id") or assum_info.get("name", "-")
        scen_info = m.get("scenario", {})
        if isinstance(scen_info, dict) and scen_info:
            info["scenario"] = scen_info.get("id") or scen_info.get("name", "-")
        info["timestamp"] = m.get("run_timestamp", "-")
    return info


def _find_most_recent_run(runs_dir: Path) -> Path | None:
    """Find the most recently modified run directory."""
    if not runs_dir.exists():
        return None
    run_dirs = [p for p in runs_dir.iterdir() if p.is_dir()]
    if not run_dirs:
        return None
    return max(run_dirs, key=lambda p: p.stat().st_mtime)


def _is_already_exported(run_dir: Path, out_dir: Path) -> bool:
    """Check if a run has already been exported to the web directory."""
    run_id = run_dir.name
    exported_manifest = out_dir / "runs" / run_id / "manifest.json"
    return exported_manifest.exists()


def _export_single_run(run_dir: Path, out: Path, force: bool = False) -> bool:
    """Export a single run. Returns True if exported, False if skipped."""
    run_id = run_dir.name
    if _is_already_exported(run_dir, out) and not force:
        echo_warning(f"Run [cyan]{run_id}[/] already exported (use --force to re-export)")
        return False

    echo_info(f"Exporting: [cyan]{run_id}[/]")
    export_web_bundle(run_dir, out / "runs" / run_id)
    return True


@main.command("export-web")
@click.option(
    "--run-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Path to the run bundle directory (default: most recent run)",
)
@click.option(
    "--out",
    default="web/static",
    type=click.Path(path_type=Path),
    help="Output directory for the web bundle (default: web/static)",
)
@click.option(
    "--all",
    "export_all",
    is_flag=True,
    help="Export all runs from the runs/ directory",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-export runs even if already exported",
)
@click.option(
    "--no-index",
    is_flag=True,
    help="Skip rebuilding the runs index after export",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts",
)
def export_web(
    run_dir: Path | None, out: Path, export_all: bool, force: bool, no_index: bool, yes: bool
) -> None:
    """Export a run bundle for web consumption.

    Converts the Parquet-based run bundle into JSON files suitable
    for the SvelteKit web frontend.

    If no --run-dir is specified, exports the most recent run (with confirmation).
    Use --all to export all runs from the runs/ directory.

    Automatically rebuilds runs/index.json after export (use --no-index to skip).
    """
    console.rule("[bold cyan]Exporting Web Bundle[/]")
    runs_dir = Path("runs")
    exported_any = False

    if export_all:
        if not runs_dir.exists():
            echo_error("No runs directory found.")
            raise SystemExit(1)
        run_dirs = sorted([p for p in runs_dir.iterdir() if p.is_dir()])
        if not run_dirs:
            echo_error("No runs found in runs/")
            raise SystemExit(1)

        echo_info(f"Found [bold]{len(run_dirs)}[/] runs")
        echo_info(f"Output: [dim]{out}[/]")
        console.print()

        exported = 0
        skipped = 0
        for rd in run_dirs:
            try:
                if _export_single_run(rd, out, force):
                    exported += 1
                else:
                    skipped += 1
            except FileNotFoundError as e:
                echo_error(f"Failed to export {rd.name}: {e}")

        console.print()
        if exported > 0:
            echo_success(f"Exported [bold green]{exported}[/] run(s) to [bold]{out}[/]")
            exported_any = True
        if skipped > 0:
            echo_info(f"Skipped [dim]{skipped}[/] already-exported run(s)")

    else:
        if run_dir is None:
            run_dir = _find_most_recent_run(runs_dir)
            if run_dir is None:
                echo_error("No runs found. Run a simulation first or specify --run-dir.")
                raise SystemExit(1)

            info = _get_run_info(run_dir)
            already_exported = _is_already_exported(run_dir, out)

            console.print()
            console.print("[bold]Most recent run:[/]")
            console.print(f"  Run ID:      [cyan]{info['run_id']}[/]")
            console.print(f"  Years:       [magenta]{info['years']}[/]")
            console.print(f"  Assumptions: [green]{info['assumptions']}[/]")
            console.print(f"  Scenario:    [yellow]{info['scenario']}[/]")
            console.print(f"  Timestamp:   [dim]{info['timestamp']}[/]")
            if already_exported:
                console.print("  Status:      [yellow]Already exported[/]")
            console.print()

            if already_exported and not force:
                echo_warning("This run has already been exported. Use --force to re-export.")
                raise SystemExit(0)

            if not yes and not click.confirm("Export this run?", default=True):
                echo_info("Cancelled.")
                raise SystemExit(0)

        run_id = run_dir.name
        run_out = out / "runs" / run_id
        echo_info(f"Source: [dim]{run_dir}[/]")
        echo_info(f"Output: [dim]{run_out}[/]")

        try:
            export_web_bundle(run_dir, run_out)
            console.print()
            echo_success(f"Web bundle exported to [bold green]{run_out}[/]")
            exported_any = True
        except FileNotFoundError as e:
            echo_error(str(e))
            raise SystemExit(1) from e

    if exported_any and not no_index:
        echo_info("Rebuilding runs index...")
        rebuild_web_index(out)
        index_path = out / "runs" / "index.json"
        echo_success(f"Index updated at [bold green]{index_path}[/]")


@main.command("rebuild-web-index")
@click.option(
    "--web-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the web directory containing runs/",
)
def rebuild_web_index_cmd(web_dir: Path) -> None:
    """Rebuild runs/index.json from all exported runs.

    Scans web_dir/runs/*/manifest.json and creates web_dir/runs/index.json.
    """
    console.rule("[bold cyan]Rebuilding Web Index[/]")
    echo_info(f"Scanning: [dim]{web_dir}[/]")

    rebuild_web_index(web_dir)

    index_path = web_dir / "runs" / "index.json"
    if not (web_dir / "runs").exists():
        index_path = web_dir / "index.json"

    console.print()
    echo_success(f"Index rebuilt at [bold green]{index_path}[/]")


@main.command("generate-story")
@click.option(
    "--run-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the run bundle directory",
)
@click.option(
    "--audience",
    default="generalist",
    type=click.Choice(["generalist", "technical", "expert"]),
    help="Target audience for the story",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    help="Output path for story.md (default: run_dir/story.md)",
)
@click.option(
    "--baseline",
    type=click.Path(exists=True, path_type=Path),
    help="Baseline run directory for comparison",
)
@click.option(
    "--offline",
    is_flag=True,
    help="Use template-based generation without LLM",
)
@click.option(
    "--force",
    is_flag=True,
    help="Regenerate even if story already exists",
)
def generate_story(
    run_dir: Path,
    audience: str,
    out: Path | None,
    baseline: Path | None,
    offline: bool,
    force: bool,
) -> None:
    """Generate a narrative story for a simulation run."""
    console.rule("[bold cyan]Generating Story[/]")

    if not STORY_AVAILABLE:
        echo_error(
            "Story generation requires the 'story' extra. "
            "Install with: pip install 'agent-zero[story]'"
        )
        raise SystemExit(1)

    output_path = out or (run_dir / "story.md")
    provenance_path = output_path.with_suffix(".story_provenance.json")

    if output_path.exists() and not force:
        echo_warning(f"Story already exists at [dim]{output_path}[/]")
        echo_info("Use --force to regenerate")
        raise SystemExit(0)

    manifest_path = run_dir / "manifest.yaml"
    timeseries_path = run_dir / "timeseries.parquet"
    if not manifest_path.exists():
        echo_error(f"Missing manifest.yaml in run directory: {run_dir}")
        raise SystemExit(1)
    if not timeseries_path.exists():
        echo_error(f"Missing timeseries.parquet in run directory: {run_dir}")
        raise SystemExit(1)

    if not offline:
        import os

        if not os.environ.get("ANTHROPIC_API_KEY"):
            echo_error(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Either set it or use --offline for template-based generation."
            )
            raise SystemExit(1)

    echo_info(f"Run directory: [dim]{run_dir}[/]")
    echo_info(f"Audience: [bold cyan]{audience}[/]")
    if baseline:
        echo_info(f"Baseline: [dim]{baseline}[/]")
    echo_info(f"Mode: [bold]{'offline (template)' if offline else 'LLM'}[/]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Generating story...", total=None)

        generator = StoryGenerator(
            run_dir=run_dir,
            audience=audience,  # type: ignore[arg-type]
            baseline_dir=baseline,
        )

        if offline:
            result: StoryOutput = generator.generate_offline()
        else:
            result = generator.generate()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.story_markdown)

    import json
    from dataclasses import asdict

    provenance_dict = asdict(result.provenance)
    provenance_dict["tools_called"] = [asdict(tc) for tc in result.provenance.tools_called]
    provenance_path.write_text(json.dumps(provenance_dict, indent=2))

    word_count = len(result.story_markdown.split())
    section_count = result.story_markdown.count("\n## ")

    console.print()
    panel_text = Text()
    panel_text.append("Output:   ", style="bold")
    panel_text.append(f"{output_path}\n", style="green")
    panel_text.append("Provenance: ", style="bold")
    panel_text.append(f"{provenance_path}\n", style="dim")
    panel_text.append("Words:    ", style="bold")
    panel_text.append(f"{word_count:,}\n")
    panel_text.append("Sections: ", style="bold")
    panel_text.append(f"{section_count}\n")
    panel_text.append("Time:     ", style="bold")
    panel_text.append(f"{result.provenance.generation_time_seconds:.1f}s")

    console.print(Panel(panel_text, title="[green]✓ Story Generated[/]", expand=False))
