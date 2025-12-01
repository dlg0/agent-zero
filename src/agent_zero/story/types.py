"""Type definitions for story data products.

These dataclasses mirror the TypeScript interfaces defined in
docs/story_data_products_schema.md for use by story generation tools.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class YearRange:
    """Simulation year range."""

    start: int
    end: int


@dataclass
class StoryContext:
    """High-level context for story generation."""

    run_id: str
    audience: Literal["generalist", "technical", "expert"]
    scenario_name: str | None
    baseline_name: str
    years: YearRange
    is_scenario_run: bool


@dataclass
class TotalEmissions:
    """Total emissions metric with trend."""

    value: float
    unit: str
    trend: Literal["up", "down", "stable"]
    delta_percent: float | None = None


@dataclass
class CumulativeEmissions:
    """Cumulative emissions metric."""

    value: float
    unit: str


@dataclass
class PeakCapacity:
    """Peak capacity metric with year."""

    value: float
    unit: str
    year: int


@dataclass
class TotalInvestment:
    """Total investment metric."""

    value: float
    unit: str


@dataclass
class AveragePrice:
    """Average price for a commodity."""

    commodity: str
    value: float
    unit: str


@dataclass
class HeadlineMetrics:
    """Key numbers for the story narrative."""

    total_emissions: TotalEmissions
    cumulative_emissions: CumulativeEmissions
    peak_capacity: PeakCapacity
    total_investment: TotalInvestment
    average_price: list[AveragePrice]


@dataclass
class Driver:
    """Factor driving simulation results.

    This schema matches the consolidated Driver interface from the web bundle.
    """

    factor: str
    contribution: float
    direction: Literal["positive", "negative", "neutral"]
    explanation: str
    related_params: list[str] = field(default_factory=list)
    related_agents: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass
class AgentTypeSummary:
    """Summary for a single agent type."""

    type: str
    count: int
    invest_count: int
    retire_count: int
    hold_count: int
    total_capacity_change: float


@dataclass
class AgentSummary:
    """Aggregated agent behaviour summary."""

    total_agents: int
    by_type: list[AgentTypeSummary]
    dominant_behaviour: str
    notable_patterns: list[str]


@dataclass
class KeyDifference:
    """Key difference between scenario and baseline."""

    metric: str
    baseline_value: float
    scenario_value: float
    delta: float
    delta_percent: float
    interpretation: str


@dataclass
class AssumptionChange:
    """Assumption change from baseline to scenario."""

    param: str
    region: str | None
    baseline: float
    scenario: float
    rationale: str


@dataclass
class ScenarioComparison:
    """Comparison with baseline run."""

    baseline_run_id: str | None
    key_differences: list[KeyDifference]
    assumption_changes: list[AssumptionChange]


@dataclass
class Caveats:
    """Mandatory limitations and warnings."""

    model_limitations: list[str] = field(default_factory=list)
    data_limitations: list[str] = field(default_factory=list)
    scenario_specific: list[str] = field(default_factory=list)
    interpretation_guidance: list[str] = field(default_factory=list)
