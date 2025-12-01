<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import RunSelector from '$lib/components/RunSelector.svelte';
  import ComparisonChart from '$lib/components/ComparisonChart.svelte';
  import ComparisonTable from '$lib/components/ComparisonTable.svelte';
  import type { RunIndexEntry, Summary, Timeseries } from '$lib/types';

  interface LoadedRun {
    runId: string;
    label: string;
    summary: Summary;
    timeseries: Timeseries;
    isBaseline?: boolean;
  }

  let runs: RunIndexEntry[] = [];
  let selectedBaseline: string | null = null;
  let selectedScenarios: string[] = [];
  let loadedRuns: LoadedRun[] = [];
  let loading = false;
  let error: string | null = null;

  const colorPalette = [
    '#14b8a6', // teal (baseline)
    '#3b82f6', // blue
    '#8b5cf6', // purple
    '#f59e0b', // amber
    '#22c55e', // green
    '#ef4444', // red
    '#ec4899', // pink
    '#06b6d4', // cyan
  ];

  async function loadRunsIndex() {
    try {
      const res = await fetch('/runs/index.json');
      if (!res.ok) throw new Error('Failed to load runs index');
      runs = await res.json();
    } catch (e) {
      error = 'Failed to load runs index';
      console.error(e);
    }
  }

  async function loadRunData(runId: string): Promise<{ summary: Summary; timeseries: Timeseries } | null> {
    try {
      const [summaryRes, timeseriesRes] = await Promise.all([
        fetch(`/runs/${runId}/summary.json`),
        fetch(`/runs/${runId}/timeseries.json`)
      ]);
      
      if (!summaryRes.ok || !timeseriesRes.ok) {
        console.warn(`Failed to load data for run ${runId}`);
        return null;
      }
      
      const summary = await summaryRes.json();
      const timeseries = await timeseriesRes.json();
      return { summary, timeseries };
    } catch (e) {
      console.error(`Error loading run ${runId}:`, e);
      return null;
    }
  }

  async function loadSelectedRuns() {
    if (!selectedBaseline && selectedScenarios.length === 0) {
      loadedRuns = [];
      return;
    }

    loading = true;
    error = null;

    const runIdsToLoad = selectedBaseline 
      ? [selectedBaseline, ...selectedScenarios]
      : selectedScenarios;

    const results = await Promise.all(
      runIdsToLoad.map(async (runId) => {
        const data = await loadRunData(runId);
        if (!data) return null;
        
        const indexEntry = runs.find(r => r.run_id === runId);
        const loaded: LoadedRun = {
          runId,
          label: indexEntry?.scenario_id || runId.split('-').slice(-1)[0],
          summary: data.summary,
          timeseries: data.timeseries,
          isBaseline: runId === selectedBaseline
        };
        return loaded;
      })
    );

    loadedRuns = results.filter((r): r is LoadedRun => r !== null);
    loading = false;
  }

  function handleSelectionChange(baseline: string | null, scenarios: string[]) {
    selectedBaseline = baseline;
    selectedScenarios = scenarios;
    
    const params = new URLSearchParams();
    if (baseline) params.set('baseline', baseline);
    if (scenarios.length > 0) params.set('scenarios', scenarios.join(','));
    
    const newUrl = scenarios.length > 0 || baseline 
      ? `?${params.toString()}` 
      : '/compare';
    goto(newUrl, { replaceState: true, noScroll: true });
    
    loadSelectedRuns();
  }

  function buildEmissionsDatasets() {
    return loadedRuns.map((run, i) => ({
      runId: run.runId,
      label: run.label,
      data: run.timeseries.map(t => ({ x: t.year, y: t.emissions })),
      color: run.isBaseline ? colorPalette[0] : colorPalette[(i % (colorPalette.length - 1)) + 1],
      isBaseline: run.isBaseline
    }));
  }

  function buildPriceDatasets() {
    return loadedRuns.map((run, i) => ({
      runId: run.runId,
      label: run.label,
      data: run.timeseries.map(t => ({ x: t.year, y: t.price })),
      color: run.isBaseline ? colorPalette[0] : colorPalette[(i % (colorPalette.length - 1)) + 1],
      isBaseline: run.isBaseline
    }));
  }

  function buildDemandDatasets() {
    return loadedRuns.map((run, i) => ({
      runId: run.runId,
      label: run.label,
      data: run.timeseries.map(t => ({ x: t.year, y: t.demand })),
      color: run.isBaseline ? colorPalette[0] : colorPalette[(i % (colorPalette.length - 1)) + 1],
      isBaseline: run.isBaseline
    }));
  }

  onMount(async () => {
    await loadRunsIndex();
    
    const baselineParam = $page.url.searchParams.get('baseline');
    const scenariosParam = $page.url.searchParams.get('scenarios');
    
    if (baselineParam) {
      selectedBaseline = baselineParam;
    }
    if (scenariosParam) {
      selectedScenarios = scenariosParam.split(',').filter(Boolean);
    }
    
    if (selectedBaseline || selectedScenarios.length > 0) {
      loadSelectedRuns();
    }
  });

  $: tableRuns = loadedRuns.map(run => ({
    runId: run.runId,
    label: run.label,
    summary: run.summary,
    isBaseline: run.isBaseline
  }));
</script>

<svelte:head>
  <title>Compare Runs | AgentZero Command Center</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
  <!-- Page Header -->
  <div>
    <div class="flex items-center gap-3 mb-2">
      <div class="w-8 h-8 rounded-md bg-accent-500/10 flex items-center justify-center">
        <svg class="w-4 h-4 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      </div>
      <h1 class="text-2xl font-semibold text-foreground">Compare Runs</h1>
    </div>
    <p class="text-sm text-muted">Side-by-side comparison of simulation results and metrics.</p>
  </div>

  <!-- Run Selector -->
  <div class="card p-4">
    <RunSelector
      {runs}
      {selectedBaseline}
      {selectedScenarios}
      onChange={handleSelectionChange}
    />
  </div>

  {#if error}
    <div class="card p-6 border-error-500/30">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-md bg-error-500/10 flex items-center justify-center">
          <svg class="w-4 h-4 text-error-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p class="text-error-500">{error}</p>
      </div>
    </div>
  {/if}

  {#if loading}
    <div class="card p-16 text-center">
      <div class="spinner mx-auto mb-4"></div>
      <p class="text-muted">Loading run data...</p>
    </div>
  {:else if loadedRuns.length > 0}
    <div class="space-y-6 fade-in">
      <!-- Key Metrics Table -->
      <div class="card p-6">
        <h2 class="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Key Metrics Comparison
        </h2>
        <ComparisonTable runs={tableRuns} />
      </div>

      <!-- Charts Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="card p-6">
          <h3 class="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-accent-500"></span>
            Emissions Over Time
          </h3>
          <ComparisonChart
            datasets={buildEmissionsDatasets()}
            title=""
            xLabel="Year"
            yLabel="Emissions (t CO₂)"
          />
        </div>

        <div class="card p-6">
          <h3 class="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-accent-500"></span>
            Electricity Price
          </h3>
          <ComparisonChart
            datasets={buildPriceDatasets()}
            title=""
            xLabel="Year"
            yLabel="Price ($/MWh)"
          />
        </div>
      </div>

      <!-- Full Width Demand Chart -->
      <div class="card p-6">
        <h3 class="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-accent-500"></span>
          Electricity Demand
        </h3>
        <ComparisonChart
          datasets={buildDemandDatasets()}
          title=""
          xLabel="Year"
          yLabel="Demand (TWh)"
        />
      </div>

      <!-- Capacity Comparison -->
      <div class="card p-6">
        <h3 class="text-sm font-semibold text-foreground mb-6 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-accent-500"></span>
          Capacity Comparison (Final Year)
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {#each ['solar', 'wind', 'battery', 'gas', 'coal', 'hydro'] as tech}
            <div class="data-panel">
              <p class="metric-label mb-3">{tech}</p>
              <div class="space-y-2">
                {#each loadedRuns as run, i}
                  {@const capacity = run.summary.total_capacity?.[tech] ?? 0}
                  <div class="flex items-center justify-between text-sm">
                    <span 
                      class="w-2 h-2 rounded-full flex-shrink-0"
                      style="background-color: {run.isBaseline ? colorPalette[0] : colorPalette[(i % (colorPalette.length - 1)) + 1]}"
                    ></span>
                    <span class="text-foreground font-mono text-xs">
                      {(capacity / 1000).toFixed(1)} GW
                    </span>
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {:else if selectedBaseline || selectedScenarios.length > 0}
    <div class="card">
      <div class="empty-state">
        <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
        </svg>
        <p class="empty-state-title">No data available</p>
        <p class="empty-state-description">The selected runs could not be loaded.</p>
      </div>
    </div>
  {:else}
    <div class="card">
      <div class="empty-state">
        <div class="w-16 h-16 rounded-full bg-accent-500/10 flex items-center justify-center mb-6">
          <svg class="w-8 h-8 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <p class="empty-state-title">Select Runs to Compare</p>
        <p class="empty-state-description">
          Choose a baseline and one or more scenarios from the selector above to begin comparison analysis.
        </p>
      </div>
    </div>
  {/if}
</div>
