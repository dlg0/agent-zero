# AgentZero Storytelling Web App Specification

## 1. Purpose

The storytelling application is the primary human-facing interface for interpreting AgentZero simulations. It enables policy analysts, technical users, and model experts to understand what the model does, how it works, and what drives results—without needing to run code themselves.

The application uses **progressive disclosure** to balance accessibility and depth, and embeds **LLM-based story generation** as a first-class capability to produce narrative explanations from structured data products.

## 2. Guiding Principles

These principles flow directly from [AgentZero Core Tenets](agentzero_core.md):

1. **Zero Black Boxes** — Every number is traceable to its source assumptions, patches, and agent decisions.
2. **Everything Linkable** — Canonical URLs for runs, assumptions, scenarios, and agents.
3. **Reproducibility by Design** — Every view shows run ID, commit hash, and CLI reproduction command.
4. **Progressive Disclosure** — Story-first for generalists; drill-down for experts.
5. **Story-First, Data-Accurate** — Narratives are generated from structured data products, never invented.
6. **Guardrails Against Misuse** — Units, validity ranges, and semantic warnings accompany all data.

## 3. User Personas

| Persona | Needs | Entry Point |
|---------|-------|-------------|
| **Policy Generalist** | Narrative explanations, key findings, "what does this mean?" | Story Mode |
| **Technical Analyst** | Charts, downloadable data, scenario comparisons, uncertainty | Scenario Explorer, Data Explorer |
| **Model Expert** | Assumptions provenance, agent decision rules, data lineage | Assumptions Browser, Agent Inspector |

## 4. Core Features

### 4.1 Run Browser (Foundation)

The Run Browser is the foundational navigation layer. All other views are anchored to specific runs.

#### 4.1.1 Run Catalogue (`/runs`)
- List all published runs with metadata:
  - Run ID, creation date
  - Year range
  - Assumptions pack name + version
  - Scenario pack name + version (if any)
  - Engine version
- Filter by: assumptions pack, scenario pack, date range, tags
- Sort by: date, run ID

#### 4.1.2 Run Detail Page (`/runs/{run_id}`)
The canonical view for a single simulation run. Contains:

- **Metadata Panel**:
  - Run ID (copyable)
  - Years simulated
  - Assumptions pack (link to `/assumptions/{pack}`)
  - Scenario pack (link to `/scenarios/{pack}`)
  - Engine version + commit hash
  - Random seed
- **Reproduction Block**:
  - Exact CLI command to reproduce this run
  - Links to download input packs
- **Quick Summary**: Key metrics (total emissions, capacity, cost) as cards
- **Navigation**: Tabs/links to Story, Data Explorer, Agent Inspector

### 4.2 Story Mode (`/runs/{run_id}/story`)

A guided, scroll-based narrative that explains:
- Key findings and headline numbers
- What drives the results
- How agents behave under this scenario
- What changed compared to baseline (if scenario applied)

#### 4.2.1 LLM-Powered Story Generation

Story generation is a **first-class design decision**. The architecture supports:

1. **Data Products** — Structured, schema-validated outputs from each run:
   - `summary.json`: headline metrics, deltas from baseline
   - `drivers.json`: ranked list of factors driving results
   - `agent_summary.json`: aggregated agent behaviour patterns
   - `scenario_diff.json`: what the scenario changed

2. **Story Tools** — Functions that operate on data products:
   - `get_headline_metrics(run_id)` → key numbers with context
   - `compare_scenarios(baseline_id, scenario_id)` → structured diff
   - `explain_agent_behaviour(run_id, agent_type)` → decision traces
   - `get_assumption_context(param, region, sector)` → source and rationale

3. **Agentic Story Generator** — An LLM agent that:
   - Receives a run ID and target audience (generalist/technical/expert)
   - Calls story tools to gather structured data
   - Generates narrative text with inline citations to data sources
   - Produces Markdown with embedded chart references

4. **Story Artefacts** — Generated stories are:
   - Cached as versioned Markdown files per run
   - Include provenance (which tools/data products were used)
   - Can be regenerated when data products update

#### 4.2.2 Story Structure

Each story follows a template:
1. **Executive Summary** (1 paragraph)
2. **Key Findings** (3–5 bullet points with numbers)
3. **What Drives These Results** (2–3 paragraphs + 1 chart)
4. **How Agents Behave** (summary of decision patterns)
5. **Scenario Impact** (if applicable: what changed vs baseline)
6. **Caveats & Limitations** (mandatory guardrails section)

Each section links to deeper views (Data Explorer, Assumptions Browser, Agent Inspector).

### 4.3 Scenario Explorer (`/scenarios` or `/compare`)

Compare baseline and scenario runs side-by-side.

- **Run Selection**: Choose baseline run + 1–N scenario runs
- **Overlay Charts**: Key metrics plotted across selected runs
- **Difference View**: Show delta (absolute and %) from baseline
- **Uncertainty Bands**: Display qualitative uncertainty where available

#### 4.3.1 Scenario Diff View (`/runs/{run_id}/diff`)
For a scenario run, show what changed from baseline:
- Tabular diff of assumptions and policy parameters
- Grouped by region/sector/tech/param
- Colour-coded: increased (↑), decreased (↓), added, removed
- Rationale column (from patches.csv)

### 4.4 Data Explorer (`/runs/{run_id}/data`)

Interactive exploration of simulation outputs.

- **Timeseries View**: Line/area charts for any metric over years
- **Agent States View**: Table of agent states per year
- **Summary Metrics View**: Cards showing aggregated results
- **Filters**: Region, sector, tech, metric, year range
- **Search**: Free-text search across dimension values
- **Lineage Links**: Click any cell → see source assumptions

#### 4.4.1 Click-Through Traceability
Every data point supports drill-down:
- Chart point → underlying timeseries rows
- Timeseries row → relevant assumptions (region, sector, tech, param, year)
- Assumption → scenario patches that modified it (if any)

### 4.5 Assumptions Browser (`/assumptions`)

Explore all assumptions across packs.

- **Global View** (`/assumptions`): Search/filter all assumptions
- **Pack View** (`/assumptions/{pack}`): Browse specific pack
- **Run-Scoped View** (`/runs/{run_id}/assumptions`): Assumptions used in a run

Each assumption displays:
- Parameter name, value, unit
- Region, sector, tech, year
- Uncertainty band
- Source/rationale (from GLOSSARY.md or inline docs)
- Semantic warnings (out of range, deprecated, etc.)
- Which runs use this assumption

### 4.6 Agent Behaviour Inspector (`/runs/{run_id}/agents`)

Understand how agents make decisions.

#### 4.6.1 Agent Catalogue
- List agent types (e.g., electricity generator, hydrogen producer)
- Show count of agents per type in this run

#### 4.6.2 Agent Detail View (`/runs/{run_id}/agents/{agent_id}`)
For each agent:
- **Identity**: Type, region, sector, tech
- **Configuration**: Foresight horizon, discount rate, decision rule name
- **Decision Rule**: Human-readable explanation of how agent decides
- **Decision Trace**: Year-by-year log of:
  - State at start of year
  - Decision made (invest, retire, hold)
  - Inputs to decision (prices, capacity, costs)
  - Outcome (new state)
- **Assumptions Used**: Which parameters influenced this agent

#### 4.6.3 Decision Trace Requirements
The simulation engine must export decision traces in `agent_states.parquet` or a companion file:
- `agent_id`, `year`, `action`, `action_inputs`, `state_before`, `state_after`

### 4.7 Download Centre (`/runs/{run_id}/download`)

Full raw artefacts for reproducibility:
- `manifest.yaml` — run metadata
- `assumptions.parquet` — resolved assumptions used
- `timeseries.parquet` — full timeseries output
- `agent_states.parquet` — agent decision traces
- `summary.json` — aggregated metrics
- Assumptions pack (zip)
- Scenario pack (zip, if applicable)

Display file sizes and checksums.

## 5. Data Architecture

### 5.1 Web Bundle Schema

Each run produces a **web bundle** for the frontend. Generated by CLI command:
```bash
agentzero export-web --run-dir runs/<run_id> --out web/runs/<run_id>
```

#### Web Bundle Contents
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
    ├── timeseries.parquet
    ├── agent_states.parquet
    └── ...
```

#### Runs Index
```
web/runs/index.json        # Catalogue of all runs with metadata
```

### 5.2 Story Data Products

For LLM story generation, structured data products with schemas:

| Data Product | Purpose | Schema |
|--------------|---------|--------|
| `summary.json` | Headline metrics | `{total_emissions, total_capacity, total_cost, delta_from_baseline}` |
| `drivers.json` | What drives results | `[{factor, contribution, direction, explanation}]` |
| `agent_summary.json` | Aggregated behaviour | `{invest_count, retire_count, dominant_action, pattern}` |
| `scenario_diff.json` | Scenario changes | `[{param, baseline_value, scenario_value, delta, rationale}]` |

### 5.3 URL Scheme

Canonical, stable URLs:

| Path | Description |
|------|-------------|
| `/runs` | Run catalogue |
| `/runs/{run_id}` | Run detail (overview) |
| `/runs/{run_id}/story` | Generated narrative |
| `/runs/{run_id}/data` | Data explorer |
| `/runs/{run_id}/agents` | Agent inspector |
| `/runs/{run_id}/agents/{agent_id}` | Agent detail |
| `/runs/{run_id}/assumptions` | Assumptions used in run |
| `/runs/{run_id}/diff` | Scenario diff (if applicable) |
| `/runs/{run_id}/download` | Download centre |
| `/assumptions` | Global assumptions browser |
| `/assumptions/{pack}` | Assumptions pack detail |
| `/scenarios/{pack}` | Scenario pack detail |
| `/compare?baseline={id}&scenarios={id1,id2}` | Scenario comparison |

## 6. Technical Architecture

### 6.1 V1: Static-First

```
┌─────────────────┐     ┌─────────────────┐
│   CLI Pipeline  │────▶│  Static Files   │
│  (Python/uv)    │     │  (JSON, Parquet)│
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   CDN / Pages   │
                        │ (Cloudflare/GH) │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   SvelteKit     │
                        │   (Static SSG)  │
                        └─────────────────┘
```

- **Frontend**: SvelteKit with static adapter
- **Data**: JSON files served from CDN; Parquet as downloads only
- **Charts**: D3.js for control and composability
- **Deployment**: Cloudflare Pages or GitHub Pages
- **Story Generation**: Offline via CLI, cached as Markdown

### 6.2 Story Generation Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Data        │────▶│  Story       │────▶│  LLM Agent   │
│  Products    │     │  Tools       │     │  (Claude)    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │  story.md    │
                                          │  (cached)    │
                                          └──────────────┘
```

CLI command:
```bash
agentzero generate-story --run-dir runs/<run_id> --audience generalist
```

## 7. Implementation Phases

### Phase 0: Foundations (1 week)
- [ ] Define web bundle JSON schemas (`docs/web_bundle_schema.md`)
- [ ] Implement `agentzero export-web` CLI command
- [ ] Extend agent states to include decision traces
- [ ] Set up SvelteKit project with static adapter
- [ ] Deploy placeholder to Cloudflare/GitHub Pages

### Phase 1: Run Browser MVP (2 weeks)
- [ ] Run Catalogue page (`/runs`)
- [ ] Run Detail page (`/runs/{run_id}`)
- [ ] Basic Data Explorer with 3 key charts
- [ ] Download Centre
- [ ] Reproduction command display

### Phase 2: Story Generation (2 weeks)
- [ ] Define story data products and schemas
- [ ] Implement story tools (Python functions)
- [ ] Create LLM story generator with tool calling
- [ ] Implement `agentzero generate-story` CLI
- [ ] Story Mode view (`/runs/{run_id}/story`)

### Phase 3: Scenario Explorer (1–2 weeks)
- [ ] Scenario diff view (`/runs/{run_id}/diff`)
- [ ] Multi-run comparison page (`/compare`)
- [ ] Overlay charts with baseline/scenario toggle

### Phase 4: Assumptions Browser (1 week)
- [ ] Global assumptions search/filter
- [ ] Pack detail views
- [ ] Click-through from Data Explorer → Assumptions

### Phase 5: Agent Inspector (2 weeks)
- [ ] Agent catalogue view
- [ ] Agent detail with decision rule display
- [ ] Decision trace timeline visualisation
- [ ] Link from story/charts to relevant agents

## 8. Future Roadmap (Post-V1)

### 8.1 Web-Triggered Simulations
- Add FastAPI backend for job submission
- Queue runs with Celery/Redis or similar
- Real-time progress updates via WebSocket
- Results appear in Run Catalogue when complete

### 8.2 Interactive Scenario Builder
- UI for composing scenario patches
- Preview diff before running
- Save as scenario pack to Git repo
- Fork existing scenarios

### 8.3 Advanced Features
- Saved views and dashboards
- Formal lineage graph (OpenLineage-style DAG)
- Jupyter notebook integration hooks
- Collaborative annotations on runs
- Version comparison (same scenario, different engine versions)

## 9. Appendix: CLI Commands for Web App

```bash
# Export a run for web consumption
agentzero export-web --run-dir runs/<run_id> --out web/runs/<run_id>

# Generate story for a run
agentzero generate-story --run-dir runs/<run_id> --audience generalist|technical|expert

# Rebuild runs index
agentzero rebuild-web-index --web-dir web/

# Validate web bundle
agentzero validate-web-bundle web/runs/<run_id>
```
