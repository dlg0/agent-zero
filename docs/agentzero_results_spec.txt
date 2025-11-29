
# AgentZero Results Data Product Specification (Option A)

## 1. Purpose
The results data product is a structured, schema-validated artifact representing the full output of an AgentZero simulation run. It is designed to be unambiguous, analysable, reproducible, and safe for downstream use.

## 2. Composition
A results bundle consists of:

### 2.1 `timeseries.parquet` (or `.csv` fallback)
A tidy long-form table capturing annual model outputs.

**Columns:**
- `year` (int)
- `region` (string)
- `commodity` (string)
- `price` (float)
- `demand` (float)
- `supply` (float)
- `emissions` (float)
- `scenario_id` (string)
- `assumptions_id` (string)
- `run_id` (string)

### 2.2 `agent_states.parquet`
A record of agent capacity, decisions, and states.

**Columns:**
- `agent_id`
- `agent_type`
- `region`
- `year`
- `capacity`
- `investment`
- `expected_price`
- `other_state_vars` (JSON or struct)

### 2.3 `summary.json`
Headline metrics:
- cumulative emissions,
- average prices,
- investment totals,
- peak capacity,
- security-of-supply indicators.

### 2.4 `manifest.yaml`
Complete lineage:
- model version & commit,
- assumptions pack ID + hash,
- scenario pack ID + hash,
- run timestamp,
- random seed.

## 3. Behaviour
- All fields carry units.
- All columns define explicit types.
- Unknown future consumers cannot misuse the data because the bundle embeds guardrails.

## 4. Validation
A `results.schema.json` file ensures:
- type correctness,
- allowed ranges,
- missing-field detection,
- semantic checks (e.g., negative emissions warnings).

