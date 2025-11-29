
# AgentZero Storytelling Web App Specification (Option B)

## 1. Purpose
The storytelling application is the primary human-facing interface for interpreting AgentZero simulations. It uses progressive disclosure to balance accessibility and depth.

## 2. User Personas
1. **Policy generalist** – wants narrative explanations.
2. **Technical analyst** – wants charts, downloadable data, and scenario comparisons.
3. **Model expert** – drills into assumptions, agent rules, and data lineage.

## 3. Core Features
### 3.1 Interactive Story Mode
A guided, scroll-based narrative:
- Key findings,
- What drives results,
- How agents behave,
- What changed under this scenario.

### 3.2 Scenario Explorer
- Select baseline + scenario packs,
- Compare side-by-side,
- Run ensembles,
- Display uncertainty bands (qualitative only).

### 3.3 Data Explorer
Expose:
- timeseries tables,
- agent states,
- summary metrics,
- lineage.

Filtered, searchable, dimension-aware.

### 3.4 Assumptions Browser
Every parameter:
- searchable,
- sourced,
- documented,
- with semantic warnings.

### 3.5 Agent Behaviour Inspector
For each agent:
- its decision rule,
- its foresight configuration,
- its actions over time.

### 3.6 Download Centre
Full raw artifacts:
- assumptions,
- scenario patches,
- results bundles,
- model commit hash.

## 4. Technical Architecture
- **Frontend:** SvelteKit or React, with rich D3/Plotly visualisation.
- **Backend:** static or serverless (FastAPI optional).
- **Data:** directly read Parquet/CSV; cached summaries for speed.
- **Deployment:** GitHub Pages, Cloudflare Pages, or lightweight container.

## 5. Principles
- Zero black boxes.
- Everything linkable and searchable.
- Story-first, data-accurate.
- Designed for policy impact.
