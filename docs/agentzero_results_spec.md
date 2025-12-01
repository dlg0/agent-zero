
# AgentZero Results Data Product Specification

## 1. Purpose

The results data product is a structured, schema-validated artifact representing the full output of an AgentZero simulation run. It is designed to be unambiguous, analysable, reproducible, and safe for downstream use.

## 2. Composition

A results bundle consists of:

### 2.1 `timeseries.parquet` (or `.csv` fallback)

A tidy table capturing annual model outputs—long on dimensions (one row per year/region/commodity), wide on metrics (separate columns for each measured variable).

**Columns:**
| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `year` | int | — | Simulation year |
| `region` | string | — | Geographic region identifier |
| `commodity` | string | — | Traded physical commodity (e.g., "electricity", "hydrogen") |
| `price` | float | USD/MWh | Market clearing price |
| `demand` | float | MWh | Total demand |
| `supply` | float | MWh | Total supply |
| `emissions` | float | tCO2e | System-level emissions for this (year, region) tuple, repeated per commodity row |
| `scenario_id` | string | — | Scenario pack identifier |
| `assumptions_id` | string | — | Assumptions pack identifier |
| `run_id` | string | — | Unique run identifier |

**Notes:**
- `emissions` represents total system emissions per (year, region), not per-commodity. Consumers should not sum emissions across commodity rows.
- Carbon price is a policy parameter, not a traded commodity; it does not appear in this table.

### 2.2 `agent_states.parquet`

A record of agent capacity, decisions, and states per simulation year.

**Columns:**
| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `year` | int | — | Simulation year |
| `agent_id` | string | — | Unique agent identifier |
| `agent_type` | string | — | Agent class (e.g., "ElectricityProducer") |
| `region` | string | — | Agent's operating region |
| `capacity` | float | MW | Installed capacity |
| `investment` | float | MW | Capacity invested this year |
| `expected_price` | float | USD/MWh | Agent's expected price for its primary commodity at decision time |
| `other_state_vars` | JSON | — | Additional agent state (sector, tech, cash, horizon, vintage, params) |

**Notes:**
- `expected_price` captures the agent's belief about future prices when making investment decisions. This is required for ex-post analysis of agent forecasting accuracy.
- `other_state_vars` contents are model-version-specific; consumers should check `engine_version` in the manifest.

### 2.3 `summary.json`

Headline metrics for quick analysis:

| Metric | Type | Description |
|--------|------|-------------|
| `run_id` | string | Unique run identifier |
| `created` | string | ISO 8601 timestamp |
| `cumulative_emissions` | float | Sum of annual emissions (tCO2e) |
| `average_prices` | object | Mean price by commodity (USD/MWh) |
| `investment_totals` | object | Total and by-agent-type investment (MW) |
| `peak_capacity` | object | Maximum capacity by agent type (MW) |
| `peak_emissions` | float | Maximum annual emissions (tCO2e) |
| `year_net_zero` | int or null | First year emissions reach minimum |
| `security_of_supply` | object | Per-commodity shortage frequency and min supply/demand ratio |

### 2.4 `manifest.yaml`

Complete lineage and provenance:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Unique run identifier |
| `run_timestamp` | string | ISO 8601 timestamp of run execution |
| `engine_version` | string | AgentZero package version (from `agent_zero.__version__`) |
| `seed` | int | Random seed used for reproducibility |
| `years` | list[int] | Simulation year range |
| `assumptions` | object | `{id, hash, version}` from assumptions pack |
| `scenario` | object | `{id, hash, version}` from scenario pack (null if baseline) |
| `schema_versions` | object | Schema versions used: `{assumptions, scenario, results}` |
| `units` | object | Unit definitions for timeseries and agent_states columns |

**Notes:**
- Units are defined once per field in the manifest, not repeated per row.
- `schema_versions.results` indicates which version of this spec the bundle conforms to.

## 3. Behaviour

- **Units**: All numeric fields have defined units, specified in `manifest.yaml` under `units`.
- **Types**: All columns have explicit types as documented above.
- **Guardrails**: The bundle is self-describing; unknown consumers can interpret it safely using the embedded manifest and schema version.

## 4. Validation

A `results.schema.json` file ensures:
- Type correctness for all columns
- Required field presence
- Allowed ranges (e.g., capacity ≥ 0, prices ≥ 0)
- Semantic warnings (e.g., negative emissions flagged but allowed for CCS scenarios)

Validation may be run via `agentzero validate-outputs <run_dir>`.
