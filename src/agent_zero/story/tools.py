"""Tool functions for LLM story generation.

These tools load data from web bundle exports and return structured
dataclasses that can be used by LLMs to generate narrative content.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from agent_zero.story.types import (
    AgentSummary,
    AgentTypeSummary,
    AssumptionChange,
    AveragePrice,
    Caveats,
    CumulativeEmissions,
    Driver,
    HeadlineMetrics,
    KeyDifference,
    PeakCapacity,
    ScenarioComparison,
    StoryContext,
    TotalEmissions,
    TotalInvestment,
    YearRange,
)

DEFAULT_MODEL_LIMITATIONS = [
    "Model results are projections based on simplified representations of complex systems",
    "Agent behaviour is based on stylized decision rules, not actual market participants",
    "Technology costs and performance are based on current estimates and may change",
    "Policy and regulatory changes may not be fully captured",
]

DEFAULT_INTERPRETATION_GUIDANCE = [
    "Results should be interpreted as directional trends rather than precise forecasts",
    "Comparisons between scenarios are more reliable than absolute values",
    "Consider the full range of uncertainty around any projection",
]


def _load_json_dict(path: Path) -> dict[str, Any] | None:
    """Load JSON file as dict, returning None if it doesn't exist or is not a dict."""
    if not path.exists():
        return None
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    return None


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load JSON file as list, returning empty list if it doesn't exist or is not a list."""
    if not path.exists():
        return []
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def _load_yaml(path: Path) -> dict[str, Any] | None:
    """Load YAML file, returning None if it doesn't exist."""
    if not path.exists():
        return None
    with path.open() as f:
        return yaml.safe_load(f)


def _load_manifest(run_dir: Path) -> dict[str, Any] | None:
    """Load manifest from either JSON or YAML format."""
    manifest = _load_json_dict(run_dir / "manifest.json")
    if manifest is None:
        manifest = _load_yaml(run_dir / "manifest.yaml")
    return manifest


def get_story_context(run_dir: Path) -> StoryContext | None:
    """Load run manifest and return story context.

    Args:
        run_dir: Path to the run directory containing manifest.json or manifest.yaml

    Returns:
        StoryContext with run information, or None if manifest not found
    """
    manifest = _load_manifest(run_dir)
    if manifest is None:
        return None

    run_id = manifest.get("run_id", run_dir.name)

    years_data = manifest.get("years", {})
    if isinstance(years_data, list):
        years = YearRange(start=min(years_data), end=max(years_data))
    elif isinstance(years_data, dict):
        years = YearRange(
            start=years_data.get("start", 2024),
            end=years_data.get("end", 2050),
        )
    else:
        years = YearRange(start=2024, end=2050)

    assumptions = manifest.get("assumptions", manifest.get("assumptions_manifest", {}))
    scenario = manifest.get("scenario", manifest.get("scenario_manifest"))

    baseline_name = assumptions.get("id", "baseline") if assumptions else "baseline"
    scenario_name = scenario.get("id") if scenario else None
    is_scenario = scenario is not None

    return StoryContext(
        run_id=run_id,
        audience="generalist",
        scenario_name=scenario_name,
        baseline_name=baseline_name,
        years=years,
        is_scenario_run=is_scenario,
    )


def get_headline_metrics(run_dir: Path) -> HeadlineMetrics | None:
    """Load summary and timeseries data to compute headline metrics.

    Args:
        run_dir: Path to the run directory

    Returns:
        HeadlineMetrics with key numbers for narrative, or None if data not found
    """
    summary = _load_json_dict(run_dir / "summary.json")
    if summary is None:
        return None

    timeseries_list = _load_json_list(run_dir / "timeseries.json")

    peak_emissions = summary.get("peak_emissions", 0.0)
    cumulative = summary.get("cumulative_emissions", 0.0)

    if timeseries_list:
        emissions_by_year: dict[int, float] = {}
        for row in timeseries_list:
            year = row.get("year", 0)
            emissions = row.get("emissions", 0.0)
            emissions_by_year[year] = emissions_by_year.get(year, 0) + emissions

        years_sorted = sorted(emissions_by_year.keys())
        if len(years_sorted) >= 2:
            first_val = emissions_by_year[years_sorted[0]]
            last_val = emissions_by_year[years_sorted[-1]]
            if last_val < first_val * 0.95:
                trend: str = "down"
            elif last_val > first_val * 1.05:
                trend = "up"
            else:
                trend = "stable"
        else:
            trend = "stable"

        peak_year = (
            max(emissions_by_year, key=lambda y: emissions_by_year[y])
            if emissions_by_year
            else 2024
        )

        price_data: dict[str, list[float]] = {}
        for row in timeseries_list:
            commodity = row.get("commodity", "unknown")
            price = row.get("price")
            if price is not None:
                price_data.setdefault(commodity, []).append(price)
        average_prices = [
            AveragePrice(
                commodity=comm,
                value=sum(prices) / len(prices),
                unit="USD/MWh",
            )
            for comm, prices in price_data.items()
            if prices
        ]

        total_investment_val = sum(
            row.get("investment", 0.0) for row in timeseries_list if "investment" in row
        )
    else:
        trend = "stable"
        peak_year = 2024
        average_prices = []
        total_investment_val = 0.0

    return HeadlineMetrics(
        total_emissions=TotalEmissions(
            value=peak_emissions,
            unit="MtCO2e",
            trend=trend,  # type: ignore[arg-type]
        ),
        cumulative_emissions=CumulativeEmissions(
            value=cumulative,
            unit="MtCO2e",
        ),
        peak_capacity=PeakCapacity(
            value=peak_emissions,
            unit="MW",
            year=peak_year,
        ),
        total_investment=TotalInvestment(
            value=total_investment_val,
            unit="USD",
        ),
        average_price=average_prices,
    )


def get_drivers(run_dir: Path) -> list[Driver]:
    """Load or compute drivers of simulation results.

    Args:
        run_dir: Path to the run directory

    Returns:
        List of Driver objects ranked by contribution magnitude
    """
    drivers_data = _load_json_list(run_dir / "drivers.json")
    if drivers_data:
        return [
            Driver(
                factor=d.get("factor", "unknown"),
                contribution=d.get("contribution", 0.0),
                direction=d.get("direction", "positive"),
                explanation=d.get("explanation", ""),
                related_params=d.get("related_params", []),
                related_agents=d.get("related_agents", []),
                evidence=d.get("evidence", []),
            )
            for d in drivers_data
        ]

    summary = _load_json_dict(run_dir / "summary.json")
    timeseries = _load_json_list(run_dir / "timeseries.json")
    manifest = _load_manifest(run_dir)

    drivers: list[Driver] = []

    if summary and summary.get("year_net_zero"):
        drivers.append(
            Driver(
                factor="Decarbonization pathway",
                contribution=0.8,
                direction="positive",
                explanation=f"System reaches net-zero by {summary['year_net_zero']}",
                evidence=["summary.json: year_net_zero"],
            )
        )

    if manifest:
        scenario = manifest.get("scenario", manifest.get("scenario_manifest"))
        if scenario and scenario.get("id"):
            drivers.append(
                Driver(
                    factor="Scenario assumptions",
                    contribution=0.6,
                    direction="positive",
                    explanation=f"Scenario '{scenario['id']}' modifies baseline assumptions",
                    evidence=["manifest: scenario_id"],
                )
            )

    if timeseries:
        price_changes: dict[str, dict[str, tuple[int, float]]] = {}
        for row in timeseries:
            commodity = row.get("commodity", "unknown")
            year = row.get("year", 0)
            price = row.get("price")
            if price is not None:
                if commodity not in price_changes:
                    price_changes[commodity] = {"first": (year, price), "last": (year, price)}
                else:
                    if year < price_changes[commodity]["first"][0]:
                        price_changes[commodity]["first"] = (year, price)
                    if year > price_changes[commodity]["last"][0]:
                        price_changes[commodity]["last"] = (year, price)

        for commodity, data in price_changes.items():
            first_price = data["first"][1]
            last_price = data["last"][1]
            if first_price > 0:
                change_pct = (last_price - first_price) / first_price
                if abs(change_pct) > 0.1:
                    drivers.append(
                        Driver(
                            factor=f"{commodity.title()} price trajectory",
                            contribution=abs(change_pct),
                            direction="negative" if change_pct < 0 else "positive",
                            explanation=(
                                f"{commodity.title()} prices "
                                f"{'decreased' if change_pct < 0 else 'increased'} "
                                f"by {abs(change_pct) * 100:.0f}%"
                            ),
                            evidence=[f"timeseries.json: {commodity} price"],
                        )
                    )

    drivers.sort(key=lambda d: abs(d.contribution), reverse=True)
    return drivers


def get_agent_summary(run_dir: Path) -> AgentSummary | None:
    """Load agent data and compute behaviour summary.

    Args:
        run_dir: Path to the run directory

    Returns:
        AgentSummary with aggregated agent behaviour, or None if data not found
    """
    agents_list = _load_json_list(run_dir / "agents.json")
    traces_list = _load_json_list(run_dir / "agent_traces.json")

    if not agents_list and not traces_list:
        return None

    by_type: dict[str, AgentTypeSummary] = {}
    agent_types: dict[str, str] = {}

    for agent in agents_list:
        agent_id = agent.get("agent_id", "")
        agent_type = agent.get("agent_type", "Unknown")
        agent_types[agent_id] = agent_type

        if agent_type not in by_type:
            by_type[agent_type] = AgentTypeSummary(
                type=agent_type,
                count=0,
                invest_count=0,
                retire_count=0,
                hold_count=0,
                total_capacity_change=0.0,
            )
        by_type[agent_type] = AgentTypeSummary(
            type=by_type[agent_type].type,
            count=by_type[agent_type].count + 1,
            invest_count=by_type[agent_type].invest_count,
            retire_count=by_type[agent_type].retire_count,
            hold_count=by_type[agent_type].hold_count,
            total_capacity_change=by_type[agent_type].total_capacity_change,
        )

    for trace in traces_list:
        agent_id = trace.get("agent_id", "")
        agent_type = agent_types.get(agent_id, "Unknown")
        action_data = trace.get("action", {})

        if agent_type not in by_type:
            by_type[agent_type] = AgentTypeSummary(
                type=agent_type,
                count=1,
                invest_count=0,
                retire_count=0,
                hold_count=0,
                total_capacity_change=0.0,
            )

        current = by_type[agent_type]
        invest = action_data.get("invest", {})
        retire = action_data.get("retire", {})

        invest_amt = sum(invest.values()) if isinstance(invest, dict) else 0
        retire_amt = sum(retire.values()) if isinstance(retire, dict) else 0

        if invest_amt > 0:
            by_type[agent_type] = AgentTypeSummary(
                type=current.type,
                count=current.count,
                invest_count=current.invest_count + 1,
                retire_count=current.retire_count,
                hold_count=current.hold_count,
                total_capacity_change=current.total_capacity_change + invest_amt,
            )
        elif retire_amt > 0:
            by_type[agent_type] = AgentTypeSummary(
                type=current.type,
                count=current.count,
                invest_count=current.invest_count,
                retire_count=current.retire_count + 1,
                hold_count=current.hold_count,
                total_capacity_change=current.total_capacity_change - retire_amt,
            )
        else:
            by_type[agent_type] = AgentTypeSummary(
                type=current.type,
                count=current.count,
                invest_count=current.invest_count,
                retire_count=current.retire_count,
                hold_count=current.hold_count + 1,
                total_capacity_change=current.total_capacity_change,
            )

    by_type_list = list(by_type.values())
    total_invest = sum(t.invest_count for t in by_type_list)
    total_retire = sum(t.retire_count for t in by_type_list)
    total_hold = sum(t.hold_count for t in by_type_list)

    if total_invest >= total_retire and total_invest >= total_hold:
        dominant = "investment"
    elif total_retire >= total_invest and total_retire >= total_hold:
        dominant = "retirement"
    else:
        dominant = "holding"

    patterns: list[str] = []
    for summary in by_type_list:
        if summary.invest_count > summary.retire_count * 2:
            patterns.append(f"{summary.type} agents are actively investing")
        elif summary.retire_count > summary.invest_count * 2:
            patterns.append(f"{summary.type} agents are retiring capacity")

    return AgentSummary(
        total_agents=len(agents_list) if agents_list else len(set(agent_types.values())),
        by_type=by_type_list,
        dominant_behaviour=dominant,
        notable_patterns=patterns,
    )


def compare_scenarios(run_dir: Path, baseline_dir: Path | None = None) -> ScenarioComparison | None:
    """Compare two runs and compute deltas for key metrics.

    Args:
        run_dir: Path to the scenario run directory
        baseline_dir: Path to the baseline run directory, or None to skip comparison

    Returns:
        ScenarioComparison with deltas, or None if baseline not provided or data missing
    """
    if baseline_dir is None:
        return None

    scenario_summary = _load_json_dict(run_dir / "summary.json")
    baseline_summary = _load_json_dict(baseline_dir / "summary.json")

    if scenario_summary is None or baseline_summary is None:
        return None

    baseline_manifest = _load_manifest(baseline_dir)

    baseline_run_id = baseline_manifest.get("run_id") if baseline_manifest else baseline_dir.name

    key_differences: list[KeyDifference] = []

    metrics_to_compare = [
        ("peak_emissions", "Peak Emissions"),
        ("cumulative_emissions", "Cumulative Emissions"),
        ("year_net_zero", "Year of Net Zero"),
    ]

    for metric_key, metric_name in metrics_to_compare:
        baseline_val = baseline_summary.get(metric_key)
        scenario_val = scenario_summary.get(metric_key)

        if baseline_val is not None and scenario_val is not None:
            delta = scenario_val - baseline_val
            delta_pct = (delta / baseline_val * 100) if baseline_val != 0 else 0.0

            if abs(delta_pct) > 1.0:
                if delta > 0:
                    interpretation = f"{metric_name} increased by {abs(delta_pct):.1f}%"
                else:
                    interpretation = f"{metric_name} decreased by {abs(delta_pct):.1f}%"

                key_differences.append(
                    KeyDifference(
                        metric=metric_name,
                        baseline_value=float(baseline_val),
                        scenario_value=float(scenario_val),
                        delta=float(delta),
                        delta_percent=float(delta_pct),
                        interpretation=interpretation,
                    )
                )

    assumption_changes: list[AssumptionChange] = []

    scenario_diff = _load_json_list(run_dir / "scenario_diff.json")
    for diff in scenario_diff:
        assumption_changes.append(
            AssumptionChange(
                param=diff.get("param", "unknown"),
                region=diff.get("region"),
                baseline=diff.get("baseline", 0.0),
                scenario=diff.get("scenario", 0.0),
                rationale=diff.get("rationale", ""),
            )
        )

    return ScenarioComparison(
        baseline_run_id=baseline_run_id,
        key_differences=key_differences,
        assumption_changes=assumption_changes,
    )


def get_caveats(run_dir: Path) -> Caveats:
    """Return model limitations and scenario-specific caveats.

    Args:
        run_dir: Path to the run directory

    Returns:
        Caveats object with standard and scenario-specific limitations
    """
    manifest = _load_manifest(run_dir)

    scenario_specific: list[str] = []

    if manifest:
        scenario = manifest.get("scenario", manifest.get("scenario_manifest"))
        if scenario:
            description = scenario.get("description", "")
            if description:
                scenario_specific.append(f"Scenario context: {description}")

            caveats_list = scenario.get("caveats", [])
            if isinstance(caveats_list, list):
                scenario_specific.extend(caveats_list)

    return Caveats(
        model_limitations=list(DEFAULT_MODEL_LIMITATIONS),
        data_limitations=[],
        scenario_specific=scenario_specific,
        interpretation_guidance=list(DEFAULT_INTERPRETATION_GUIDANCE),
    )


def explain_agent_behaviour(run_dir: Path, agent_type: str) -> dict[str, Any]:
    """Filter agent traces to specific type and summarize decision patterns.

    Args:
        run_dir: Path to the run directory
        agent_type: The agent type to filter and explain

    Returns:
        Structured explanation of agent behaviour patterns
    """
    agents_list = _load_json_list(run_dir / "agents.json")
    traces_list = _load_json_list(run_dir / "agent_traces.json")

    matching_agents = [
        a for a in agents_list if a.get("agent_type", "").lower() == agent_type.lower()
    ]
    agent_ids = {a.get("agent_id") for a in matching_agents}

    matching_traces = [t for t in traces_list if t.get("agent_id") in agent_ids]

    if not matching_agents and not matching_traces:
        return {
            "agent_type": agent_type,
            "found": False,
            "message": f"No agents of type '{agent_type}' found in this run",
        }

    invest_count = 0
    retire_count = 0
    hold_count = 0
    total_invest_amount = 0.0
    total_retire_amount = 0.0
    decisions_by_year: dict[int, dict[str, int]] = {}

    for trace in matching_traces:
        action = trace.get("action", {})
        year = trace.get("year", 0)

        invest = action.get("invest", {})
        retire = action.get("retire", {})

        invest_amt = sum(invest.values()) if isinstance(invest, dict) else 0
        retire_amt = sum(retire.values()) if isinstance(retire, dict) else 0

        if year not in decisions_by_year:
            decisions_by_year[year] = {"invest": 0, "retire": 0, "hold": 0}

        if invest_amt > 0:
            invest_count += 1
            total_invest_amount += invest_amt
            decisions_by_year[year]["invest"] += 1
        elif retire_amt > 0:
            retire_count += 1
            total_retire_amount += retire_amt
            decisions_by_year[year]["retire"] += 1
        else:
            hold_count += 1
            decisions_by_year[year]["hold"] += 1

    total_decisions = invest_count + retire_count + hold_count

    if invest_count >= retire_count and invest_count >= hold_count:
        dominant_pattern = "investment-focused"
    elif retire_count >= invest_count and retire_count >= hold_count:
        dominant_pattern = "retirement-focused"
    else:
        dominant_pattern = "holding"

    observations: list[str] = []
    if total_decisions > 0:
        if invest_count > 0:
            observations.append(
                f"Made {invest_count} investment decisions "
                f"({invest_count / total_decisions * 100:.0f}% of decisions)"
            )
        if retire_count > 0:
            observations.append(
                f"Made {retire_count} retirement decisions "
                f"({retire_count / total_decisions * 100:.0f}% of decisions)"
            )
        if hold_count > 0:
            observations.append(
                f"Made {hold_count} hold decisions "
                f"({hold_count / total_decisions * 100:.0f}% of decisions)"
            )

    return {
        "agent_type": agent_type,
        "found": True,
        "agent_count": len(matching_agents),
        "total_decisions": total_decisions,
        "invest_count": invest_count,
        "retire_count": retire_count,
        "hold_count": hold_count,
        "total_invest_amount": total_invest_amount,
        "total_retire_amount": total_retire_amount,
        "dominant_pattern": dominant_pattern,
        "observations": observations,
        "decisions_by_year": decisions_by_year,
    }


def to_dict(obj: Any) -> dict[str, Any] | list[Any] | Any:
    """Convert dataclass or list of dataclasses to dict for JSON serialization.

    Args:
        obj: A dataclass instance or list of dataclass instances

    Returns:
        Dictionary representation suitable for JSON serialization
    """
    if obj is None:
        return None
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return obj
