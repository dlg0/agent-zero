# Web Bundle JSON Schema Specification

This document defines the JSON schemas for the AgentZero web application. These schemas form the contract between the Python CLI `export-web` command and the SvelteKit frontend.

## Overview

Each simulation run produces a **web bundle** exported via:

```bash
agentzero export-web --run-dir runs/<run_id> --out web/runs/<run_id>
```

### Bundle Structure

```
web/runs/<run_id>/
├── manifest.json          # Run metadata, IDs, hashes
├── summary.json           # Headline metrics, cards data
├── timeseries.json        # Denormalised timeseries for charts
├── agents.json            # Agent catalogue + configs
├── agent_traces.json      # Decision traces per agent
├── assumptions_used.json  # Assumptions relevant to this run
├── scenario_diff.json     # Diff from baseline (if scenario run)
├── drivers.json           # Ranked factors driving results
└── downloads/             # Symlinks or copies of raw files

web/runs/index.json        # Catalogue of all runs
```

---

## 1. manifest.json

Run metadata for identification, reproducibility, and lineage tracking.

### Schema

```typescript
interface Manifest {
  /** Unique run identifier (hash-based) */
  run_id: string;
  
  /** ISO 8601 timestamp when run was created */
  created_at: string;
  
  /** Engine version used (e.g., "0.1.0") */
  engine_version: string;
  
  /** Git commit hash of the engine at run time */
  commit_hash: string | null;
  
  /** Year range for the simulation */
  years: {
    start: number;
    end: number;
  };
  
  /** Reference to assumptions pack used */
  assumptions: {
    id: string;
    version: string;
    hash: string;
  };
  
  /** Reference to scenario pack (null if baseline run) */
  scenario: {
    id: string;
    version: string;
    hash: string;
  } | null;
  
  /** Random seed used for reproducibility */
  seed: number;
  
  /** CLI command to reproduce this exact run */
  reproduction_command: string;
  
  /** Schema versions for validation */
  schema_versions: {
    assumptions: string;
    scenario: string | null;
    results: string;
  };
  
  /** Unit definitions for all numeric fields */
  units: {
    timeseries: Record<string, string | null>;
    agent_states: Record<string, string | null>;
  };
}
```

### Example

```json
{
  "run_id": "run_b3f7a2c1",
  "created_at": "2024-11-30T10:15:30.000Z",
  "engine_version": "0.1.0",
  "commit_hash": "a1b2c3d4e5f6",
  "years": {
    "start": 2024,
    "end": 2050
  },
  "assumptions": {
    "id": "baseline",
    "version": "1.0.0",
    "hash": "sha256:abc123..."
  },
  "scenario": {
    "id": "high_growth",
    "version": "1.0.0",
    "hash": "sha256:def456..."
  },
  "seed": 42,
  "reproduction_command": "agentzero run --assum baseline --scen high_growth --years 2024:2050 --seed 42",
  "schema_versions": {
    "assumptions": "1.0.0",
    "scenario": "1.0.0",
    "results": "1.0.0"
  },
  "units": {
    "timeseries": {
      "year": null,
      "region": null,
      "commodity": null,
      "price": "USD/MWh",
      "demand": "MWh",
      "supply": "MWh",
      "emissions": "tCO2e"
    },
    "agent_states": {
      "year": null,
      "agent_id": null,
      "agent_type": null,
      "region": null,
      "capacity": "MW",
      "investment": "MW",
      "expected_price": "USD/MWh"
    }
  }
}
```

---

## 2. summary.json

Headline metrics for dashboard cards and story generation.

### Schema

```typescript
interface Summary {
  /** Run identifier */
  run_id: string;
  
  /** ISO 8601 timestamp */
  created: string;
  
  /** Total emissions over simulation period (tCO2e) */
  total_emissions: number;
  
  /** Cumulative emissions across all years (tCO2e) */
  cumulative_emissions: number;
  
  /** Peak annual emissions (tCO2e) */
  peak_emissions: number;
  
  /** Year when net-zero is achieved (null if never) */
  year_net_zero: number | null;
  
  /** Total installed capacity by agent type (MW) */
  total_capacity: Record<string, number>;
  
  /** Peak capacity by agent type (MW) */
  peak_capacity: Record<string, number>;
  
  /** Average prices by commodity (USD/MWh) */
  average_prices: Record<string, number>;
  
  /** Investment totals */
  investment_totals: {
    total: number;
    by_agent_type: Record<string, number>;
  };
  
  /** Security of supply metrics by commodity */
  security_of_supply: Record<string, {
    shortage_frequency: number;
    min_supply_demand_ratio: number;
  }>;
  
  /** Delta from baseline (present only for scenario runs) */
  delta_from_baseline?: {
    emissions_delta: number;
    emissions_delta_pct: number;
    capacity_delta: Record<string, number>;
    price_delta: Record<string, number>;
  };
}
```

### Example

```json
{
  "run_id": "run_b3f7a2c1",
  "created": "2024-11-30T10:15:30.000Z",
  "total_emissions": 125000000,
  "cumulative_emissions": 3250000000,
  "peak_emissions": 8500000,
  "year_net_zero": 2048,
  "total_capacity": {
    "ElectricityProducer": 15000,
    "HydrogenProducer": 2500
  },
  "peak_capacity": {
    "ElectricityProducer": 18000,
    "HydrogenProducer": 3200
  },
  "average_prices": {
    "electricity": 65.5,
    "hydrogen": 3.2
  },
  "investment_totals": {
    "total": 12500,
    "by_agent_type": {
      "ElectricityProducer": 10000,
      "HydrogenProducer": 2500
    }
  },
  "security_of_supply": {
    "electricity": {
      "shortage_frequency": 0.0,
      "min_supply_demand_ratio": 1.15
    },
    "hydrogen": {
      "shortage_frequency": 0.04,
      "min_supply_demand_ratio": 0.92
    }
  },
  "delta_from_baseline": {
    "emissions_delta": -450000000,
    "emissions_delta_pct": -12.2,
    "capacity_delta": {
      "ElectricityProducer": 2000,
      "HydrogenProducer": 800
    },
    "price_delta": {
      "electricity": -5.2,
      "hydrogen": -0.3
    }
  }
}
```

---

## 3. timeseries.json

Denormalised chart data for frontend visualisations.

### Schema

```typescript
interface TimeseriesRow {
  /** Simulation year */
  year: number;
  
  /** Region code (e.g., "AUS") */
  region: string;
  
  /** Commodity type (e.g., "electricity", "hydrogen") */
  commodity: string;
  
  /** Clearing price (USD/MWh) */
  price: number;
  
  /** Total demand (MWh) */
  demand: number;
  
  /** Total supply (MWh) */
  supply: number;
  
  /** Annual emissions (tCO2e) */
  emissions: number;
  
  /** Associated scenario ID (null for baseline) */
  scenario_id: string | null;
  
  /** Associated assumptions pack ID */
  assumptions_id: string;
  
  /** Run identifier */
  run_id: string;
}

type Timeseries = TimeseriesRow[];
```

### Example

```json
[
  {
    "year": 2024,
    "region": "AUS",
    "commodity": "electricity",
    "price": 60.0,
    "demand": 250000,
    "supply": 260000,
    "emissions": 8500000,
    "scenario_id": "high_growth",
    "assumptions_id": "baseline",
    "run_id": "run_b3f7a2c1"
  },
  {
    "year": 2024,
    "region": "AUS",
    "commodity": "hydrogen",
    "price": 4.5,
    "demand": 5000,
    "supply": 4800,
    "emissions": 0,
    "scenario_id": "high_growth",
    "assumptions_id": "baseline",
    "run_id": "run_b3f7a2c1"
  },
  {
    "year": 2025,
    "region": "AUS",
    "commodity": "electricity",
    "price": 58.5,
    "demand": 255000,
    "supply": 270000,
    "emissions": 8200000,
    "scenario_id": "high_growth",
    "assumptions_id": "baseline",
    "run_id": "run_b3f7a2c1"
  }
]
```

---

## 4. agents.json

Agent catalogue with configuration details.

### Schema

```typescript
interface AgentConfig {
  /** Unique agent identifier */
  agent_id: string;
  
  /** Agent class type */
  agent_type: "ElectricityProducer" | "HydrogenProducer" | "IndustrialConsumer" | "Regulator";
  
  /** Region code */
  region: string;
  
  /** Sector (optional) */
  sector: string | null;
  
  /** Technology type (optional) */
  tech: string | null;
  
  /** Initial capacity (MW) */
  initial_capacity: number;
  
  /** Foresight horizon (years) */
  horizon: number;
  
  /** Discount rate for NPV calculations */
  discount_rate: number;
  
  /** Decision rule identifier */
  decision_rule: string;
  
  /** Vintage year (year agent was created) */
  vintage: number;
  
  /** Agent-specific parameters */
  params: Record<string, unknown>;
}

type Agents = AgentConfig[];
```

### Example

```json
[
  {
    "agent_id": "EGEN1",
    "agent_type": "ElectricityProducer",
    "region": "AUS",
    "sector": null,
    "tech": "electricity",
    "initial_capacity": 100.0,
    "horizon": 3,
    "discount_rate": 0.07,
    "decision_rule": "npv_threshold",
    "vintage": 2024,
    "params": {}
  },
  {
    "agent_id": "H2GEN1",
    "agent_type": "HydrogenProducer",
    "region": "AUS",
    "sector": null,
    "tech": "hydrogen",
    "initial_capacity": 10.0,
    "horizon": 3,
    "discount_rate": 0.07,
    "decision_rule": "npv_threshold",
    "vintage": 2024,
    "params": {}
  },
  {
    "agent_id": "IND1",
    "agent_type": "IndustrialConsumer",
    "region": "AUS",
    "sector": "Industry",
    "tech": null,
    "initial_capacity": 0.0,
    "horizon": 1,
    "discount_rate": 0.07,
    "decision_rule": "price_responsive",
    "vintage": 2024,
    "params": {}
  },
  {
    "agent_id": "REG",
    "agent_type": "Regulator",
    "region": "AUS",
    "sector": null,
    "tech": null,
    "initial_capacity": 0.0,
    "horizon": 1,
    "discount_rate": 0.0,
    "decision_rule": "policy_setter",
    "vintage": 2024,
    "params": {}
  }
]
```

---

## 5. agent_traces.json

Decision traces for agent behaviour inspection.

### Schema

```typescript
interface AgentTrace {
  /** Agent identifier */
  agent_id: string;
  
  /** Simulation year */
  year: number;
  
  /** Action taken */
  action: "invest" | "retire" | "hold" | "supply" | "none";
  
  /** Inputs to the decision */
  action_inputs: {
    current_price: number;
    expected_price: number | null;
    npv: number | null;
    capacity_headroom: number | null;
    carbon_price: number;
    [key: string]: unknown;
  };
  
  /** Agent state before action */
  state_before: {
    capacity: number;
    cash: number;
    vintage: number;
    [key: string]: unknown;
  };
  
  /** Agent state after action */
  state_after: {
    capacity: number;
    cash: number;
    vintage: number;
    investment: number;
    supply: Record<string, number>;
    emissions: number;
    [key: string]: unknown;
  };
}

type AgentTraces = AgentTrace[];
```

### Example

```json
[
  {
    "agent_id": "EGEN1",
    "year": 2024,
    "action": "invest",
    "action_inputs": {
      "current_price": 60.0,
      "expected_price": 65.5,
      "npv": 125.3,
      "capacity_headroom": 900.0,
      "carbon_price": 25.0,
      "capex": 1000.0,
      "opex": 10.0,
      "emissions_intensity": 0.5
    },
    "state_before": {
      "capacity": 100.0,
      "cash": 0.0,
      "vintage": 2024
    },
    "state_after": {
      "capacity": 110.0,
      "cash": -10000.0,
      "vintage": 2024,
      "investment": 10.0,
      "supply": {
        "electricity": 100.0
      },
      "emissions": 50.0
    }
  },
  {
    "agent_id": "EGEN1",
    "year": 2025,
    "action": "hold",
    "action_inputs": {
      "current_price": 55.0,
      "expected_price": 52.0,
      "npv": -45.2,
      "capacity_headroom": 890.0,
      "carbon_price": 30.0,
      "capex": 1000.0,
      "opex": 10.0,
      "emissions_intensity": 0.5
    },
    "state_before": {
      "capacity": 110.0,
      "cash": -10000.0,
      "vintage": 2024
    },
    "state_after": {
      "capacity": 110.0,
      "cash": -5000.0,
      "vintage": 2024,
      "investment": 0.0,
      "supply": {
        "electricity": 110.0
      },
      "emissions": 55.0
    }
  }
]
```

---

## 6. assumptions_used.json

Assumptions relevant to this simulation run.

### Schema

```typescript
interface AssumptionRow {
  /** Parameter name */
  param: string;
  
  /** Region code */
  region: string | null;
  
  /** Sector */
  sector: string | null;
  
  /** Technology type */
  tech: string | null;
  
  /** Year the value applies to */
  year: number;
  
  /** Parameter value */
  value: number;
  
  /** Unit of measurement */
  unit: string;
  
  /** Data source reference */
  source: string | null;
  
  /** Uncertainty band (optional) */
  uncertainty?: {
    low: number;
    high: number;
    distribution: "uniform" | "normal" | "triangular";
  };
}

type AssumptionsUsed = AssumptionRow[];
```

### Example

```json
[
  {
    "param": "capex",
    "region": null,
    "sector": null,
    "tech": "electricity",
    "year": 2024,
    "value": 1000.0,
    "unit": "USD/MW",
    "source": "IEA WEO 2023",
    "uncertainty": {
      "low": 800.0,
      "high": 1200.0,
      "distribution": "triangular"
    }
  },
  {
    "param": "opex",
    "region": null,
    "sector": null,
    "tech": "electricity",
    "year": 2024,
    "value": 10.0,
    "unit": "USD/MWh",
    "source": "IEA WEO 2023"
  },
  {
    "param": "emissions_intensity",
    "region": null,
    "sector": null,
    "tech": "electricity",
    "year": 2024,
    "value": 0.5,
    "unit": "tCO2e/MWh",
    "source": "IPCC AR6"
  },
  {
    "param": "discount_rate",
    "region": null,
    "sector": null,
    "tech": "electricity",
    "year": 2024,
    "value": 0.07,
    "unit": "fraction",
    "source": "Model default"
  },
  {
    "param": "initial_capacity",
    "region": null,
    "sector": null,
    "tech": "electricity",
    "year": 2024,
    "value": 100.0,
    "unit": "MW",
    "source": "AEMO ISP 2024"
  }
]
```

---

## 7. scenario_diff.json

Diff from baseline assumptions (only present for scenario runs).

### Schema

```typescript
interface ScenarioDiffRow {
  /** Parameter name */
  param: string;
  
  /** Region code */
  region: string | null;
  
  /** Sector */
  sector: string | null;
  
  /** Technology type */
  tech: string | null;
  
  /** Year the diff applies to */
  year: number;
  
  /** Value in baseline */
  baseline_value: number;
  
  /** Value in scenario */
  scenario_value: number;
  
  /** Absolute delta (scenario - baseline) */
  delta: number;
  
  /** Percentage change */
  delta_pct: number;
  
  /** Rationale for the change (from patches.csv) */
  rationale: string | null;
}

type ScenarioDiff = ScenarioDiffRow[];
```

### Example

```json
[
  {
    "param": "carbon_price",
    "region": null,
    "sector": null,
    "tech": null,
    "year": 2030,
    "baseline_value": 50.0,
    "scenario_value": 100.0,
    "delta": 50.0,
    "delta_pct": 100.0,
    "rationale": "High ambition carbon pricing pathway aligned with 1.5°C target"
  },
  {
    "param": "capex",
    "region": null,
    "sector": null,
    "tech": "hydrogen",
    "year": 2030,
    "baseline_value": 2500.0,
    "scenario_value": 1800.0,
    "delta": -700.0,
    "delta_pct": -28.0,
    "rationale": "Accelerated electrolyser cost reduction from manufacturing scale-up"
  },
  {
    "param": "demand_growth",
    "region": "AUS",
    "sector": "Industry",
    "tech": null,
    "year": 2035,
    "baseline_value": 0.02,
    "scenario_value": 0.04,
    "delta": 0.02,
    "delta_pct": 100.0,
    "rationale": "High industrial electrification scenario"
  }
]
```

---

## 8. drivers.json

Ranked factors driving simulation results (for story generation).

> **Note:** `drivers.json` may initially be an empty array (`[]`). This indicates that story generation has not yet been run for this simulation. After running `agentzero generate-story`, it will contain ranked drivers. An empty array is valid and means "not yet generated" — the frontend will display "No drivers data available. Run story generation to populate."

### Schema

```typescript
interface Driver {
  /** Factor name */
  factor: string;
  
  /** Contribution to outcome (normalised 0-1 or percentage) */
  contribution: number;
  
  /** Direction of impact */
  direction: "positive" | "negative" | "neutral";
  
  /** Human-readable explanation */
  explanation: string;
  
  /** Related parameters */
  related_params: string[];
  
  /** Related agents */
  related_agents: string[];
  
  /** Supporting evidence (optional, added by story generation) */
  evidence?: string[];
}

type Drivers = Driver[];
```

### Example

```json
[
  {
    "factor": "Carbon price trajectory",
    "contribution": 0.35,
    "direction": "positive",
    "explanation": "Rising carbon prices from $25/t to $150/t by 2050 drove accelerated retirement of high-emission capacity and investment in low-carbon alternatives.",
    "related_params": ["carbon_price", "emissions_intensity"],
    "related_agents": ["EGEN1", "H2GEN1"]
  },
  {
    "factor": "Electrolyser cost reduction",
    "contribution": 0.25,
    "direction": "positive",
    "explanation": "50% reduction in hydrogen production CAPEX enabled economic viability of green hydrogen by 2030.",
    "related_params": ["capex"],
    "related_agents": ["H2GEN1"]
  },
  {
    "factor": "Industrial demand growth",
    "contribution": 0.20,
    "direction": "negative",
    "explanation": "Higher than expected industrial electricity demand increased overall system emissions despite decarbonisation of supply.",
    "related_params": ["demand_high", "demand_low", "demand_growth"],
    "related_agents": ["IND1"]
  },
  {
    "factor": "Investment threshold behaviour",
    "contribution": 0.15,
    "direction": "neutral",
    "explanation": "Agent investment thresholds led to lumpy capacity additions, creating periodic supply-demand mismatches.",
    "related_params": ["invest_threshold", "invest_step", "max_capacity"],
    "related_agents": ["EGEN1", "H2GEN1"]
  }
]
```

---

## 9. runs/index.json

Catalogue of all available runs for the run browser.

### Schema

```typescript
interface RunIndexEntry {
  /** Unique run identifier */
  run_id: string;
  
  /** ISO 8601 timestamp */
  created_at: string;
  
  /** Year range */
  years: {
    start: number;
    end: number;
  };
  
  /** Assumptions pack identifier */
  assumptions_id: string;
  
  /** Scenario pack identifier (null for baseline) */
  scenario_id: string | null;
  
  /** Engine version */
  engine_version: string;
  
  /** Quick summary metrics for list display */
  quick_summary: {
    cumulative_emissions: number;
    year_net_zero: number | null;
  };
  
  /** Tags for filtering (optional) */
  tags?: string[];
}

type RunsIndex = RunIndexEntry[];
```

### Example

```json
[
  {
    "run_id": "run_b3f7a2c1",
    "created_at": "2024-11-30T10:15:30.000Z",
    "years": {
      "start": 2024,
      "end": 2050
    },
    "assumptions_id": "baseline",
    "scenario_id": "high_growth",
    "engine_version": "0.1.0",
    "quick_summary": {
      "cumulative_emissions": 3250000000,
      "year_net_zero": 2048
    },
    "tags": ["scenario", "high-ambition"]
  },
  {
    "run_id": "run_a1c2e3f4",
    "created_at": "2024-11-29T14:20:00.000Z",
    "years": {
      "start": 2024,
      "end": 2050
    },
    "assumptions_id": "baseline",
    "scenario_id": null,
    "engine_version": "0.1.0",
    "quick_summary": {
      "cumulative_emissions": 3700000000,
      "year_net_zero": null
    },
    "tags": ["baseline"]
  }
]
```

---

## TypeScript Type Definitions

For frontend consumption, all types are available as a single TypeScript module:

```typescript
// web_bundle.types.ts

export interface Manifest {
  run_id: string;
  created_at: string;
  engine_version: string;
  commit_hash: string | null;
  years: { start: number; end: number };
  assumptions: { id: string; version: string; hash: string };
  scenario: { id: string; version: string; hash: string } | null;
  seed: number;
  reproduction_command: string;
  schema_versions: {
    assumptions: string;
    scenario: string | null;
    results: string;
  };
  units: {
    timeseries: Record<string, string | null>;
    agent_states: Record<string, string | null>;
  };
}

export interface Summary {
  run_id: string;
  created: string;
  total_emissions: number;
  cumulative_emissions: number;
  peak_emissions: number;
  year_net_zero: number | null;
  total_capacity: Record<string, number>;
  peak_capacity: Record<string, number>;
  average_prices: Record<string, number>;
  investment_totals: {
    total: number;
    by_agent_type: Record<string, number>;
  };
  security_of_supply: Record<string, {
    shortage_frequency: number;
    min_supply_demand_ratio: number;
  }>;
  delta_from_baseline?: {
    emissions_delta: number;
    emissions_delta_pct: number;
    capacity_delta: Record<string, number>;
    price_delta: Record<string, number>;
  };
}

export interface TimeseriesRow {
  year: number;
  region: string;
  commodity: string;
  price: number;
  demand: number;
  supply: number;
  emissions: number;
  scenario_id: string | null;
  assumptions_id: string;
  run_id: string;
}

export type Timeseries = TimeseriesRow[];

export interface AgentConfig {
  agent_id: string;
  agent_type: "ElectricityProducer" | "HydrogenProducer" | "IndustrialConsumer" | "Regulator";
  region: string;
  sector: string | null;
  tech: string | null;
  initial_capacity: number;
  horizon: number;
  discount_rate: number;
  decision_rule: string;
  vintage: number;
  params: Record<string, unknown>;
}

export type Agents = AgentConfig[];

export interface AgentTrace {
  agent_id: string;
  year: number;
  action: "invest" | "retire" | "hold" | "supply" | "none";
  action_inputs: {
    current_price: number;
    expected_price: number | null;
    npv: number | null;
    capacity_headroom: number | null;
    carbon_price: number;
    [key: string]: unknown;
  };
  state_before: {
    capacity: number;
    cash: number;
    vintage: number;
    [key: string]: unknown;
  };
  state_after: {
    capacity: number;
    cash: number;
    vintage: number;
    investment: number;
    supply: Record<string, number>;
    emissions: number;
    [key: string]: unknown;
  };
}

export type AgentTraces = AgentTrace[];

export interface AssumptionRow {
  param: string;
  region: string | null;
  sector: string | null;
  tech: string | null;
  year: number;
  value: number;
  unit: string;
  source: string | null;
  uncertainty?: {
    low: number;
    high: number;
    distribution: "uniform" | "normal" | "triangular";
  };
}

export type AssumptionsUsed = AssumptionRow[];

export interface ScenarioDiffRow {
  param: string;
  region: string | null;
  sector: string | null;
  tech: string | null;
  year: number;
  baseline_value: number;
  scenario_value: number;
  delta: number;
  delta_pct: number;
  rationale: string | null;
}

export type ScenarioDiff = ScenarioDiffRow[];

export interface Driver {
  factor: string;
  contribution: number;
  direction: "positive" | "negative" | "neutral";
  explanation: string;
  related_params: string[];
  related_agents: string[];
  evidence?: string[];
}

export type Drivers = Driver[];

export interface RunIndexEntry {
  run_id: string;
  created_at: string;
  years: { start: number; end: number };
  assumptions_id: string;
  scenario_id: string | null;
  engine_version: string;
  quick_summary: {
    cumulative_emissions: number;
    year_net_zero: number | null;
  };
  tags?: string[];
}

export type RunsIndex = RunIndexEntry[];

// Complete web bundle type
export interface WebBundle {
  manifest: Manifest;
  summary: Summary;
  timeseries: Timeseries;
  agents: Agents;
  agent_traces: AgentTraces;
  assumptions_used: AssumptionsUsed;
  scenario_diff?: ScenarioDiff;
  drivers: Drivers;
}
```

---

## Alignment with Existing Code

This schema aligns with the following source files:

| Schema Field | Source Location | Notes |
|--------------|-----------------|-------|
| `manifest.years` | `results_pack.py:254` | Extracted from timeseries |
| `manifest.assumptions/scenario` | `results_pack.py:255-256` | Via `_extract_pack_ref()` |
| `manifest.units` | `results_pack.py:23-43` | `UNITS` constant |
| `summary.*` | `results_pack.py:224-234` | Computed metrics |
| `timeseries.*` | `results_pack.py:110-125` | DataFrame columns |
| `agents.*` | `types.py:28-41` | `AgentState` dataclass |
| `agent_traces.action_inputs` | `decisions.py:54-94` | Decision function params |

---

## Validation

The CLI provides validation for web bundles:

```bash
agentzero validate-web-bundle web/runs/<run_id>
```

This checks:
- All required files are present
- JSON is valid and parseable
- Required fields are present in each schema
- Type constraints are satisfied
- Cross-references between files are consistent (e.g., `run_id` matches across files)
