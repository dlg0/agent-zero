<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import AssumptionTable from '$lib/components/AssumptionTable.svelte';
  import AssumptionFilters from '$lib/components/AssumptionFilters.svelte';
  import AssumptionCard from '$lib/components/AssumptionCard.svelte';
  import TraceabilityLink from '$lib/components/TraceabilityLink.svelte';
  import type { AssumptionRow, RunIndexEntry } from '$lib/types';
  import { parseAssumptionsFilters, globalAssumptionsUrl, runUrl } from '$lib/utils/urls';

  type ViewMode = 'table' | 'cards';

  interface AggregatedAssumption extends AssumptionRow {
    runs: string[];
    assumptions_pack: string;
  }

  let runsIndex: RunIndexEntry[] = [];
  let allAssumptions: AggregatedAssumption[] = [];
  let assumptionPacks: { id: string; runs: string[] }[] = [];
  let isLoading = true;
  let error: string | null = null;
  let selectedPack: string = '';
  let viewMode: ViewMode = 'table';
  let filters = {
    region: '',
    tech: '',
    param: '',
    search: ''
  };

  onMount(async () => {
    const urlFilters = parseAssumptionsFilters($page.url.searchParams);
    if (urlFilters.param) filters.param = urlFilters.param;
    if (urlFilters.region) filters.region = urlFilters.region;
    if (urlFilters.tech) filters.tech = urlFilters.tech;

    try {
      const indexRes = await fetch('/runs/index.json');
      if (!indexRes.ok) throw new Error('Failed to load runs index');
      runsIndex = await indexRes.json();

      const packMap = new Map<string, string[]>();
      for (const run of runsIndex) {
        const existing = packMap.get(run.assumptions_id) ?? [];
        existing.push(run.run_id);
        packMap.set(run.assumptions_id, existing);
      }
      assumptionPacks = Array.from(packMap.entries()).map(([id, runs]) => ({ id, runs }));

      const assumptionsPromises = runsIndex.map(async (run) => {
        try {
          const res = await fetch(`/runs/${run.run_id}/assumptions_used.json`);
          if (!res.ok) return [];
          const data: AssumptionRow[] = await res.json();
          return data.map(a => ({
            ...a,
            runs: [run.run_id],
            assumptions_pack: run.assumptions_id
          }));
        } catch {
          return [];
        }
      });

      const results = await Promise.all(assumptionsPromises);
      allAssumptions = results.flat();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Unknown error';
    } finally {
      isLoading = false;
    }
  });

  $: displayAssumptions = selectedPack 
    ? allAssumptions.filter(a => a.assumptions_pack === selectedPack)
    : allAssumptions;

  $: regions = [...new Set(displayAssumptions.map(a => a.region).filter((r): r is string => r !== null))].sort();
  $: techs = [...new Set(displayAssumptions.map(a => a.tech).filter((t): t is string => t !== null))].sort();
  $: params = [...new Set(displayAssumptions.map(a => a.param))].sort();

  $: filteredAssumptions = displayAssumptions.filter((row) => {
    if (filters.region && row.region !== filters.region) return false;
    if (filters.tech && row.tech !== filters.tech) return false;
    if (filters.param && row.param !== filters.param) return false;
    if (filters.search) {
      const search = filters.search.toLowerCase();
      const searchable = [
        row.param,
        row.region ?? '',
        row.tech ?? '',
        row.sector ?? '',
        row.source ?? '',
        String(row.value),
        row.unit
      ].join(' ').toLowerCase();
      if (!searchable.includes(search)) return false;
    }
    return true;
  });

  function handleFilter(event: CustomEvent<typeof filters>) {
    filters = event.detail;
    updateUrl();
  }

  function updateUrl() {
    const url = globalAssumptionsUrl({
      param: filters.param || undefined,
      region: filters.region || undefined,
      tech: filters.tech || undefined
    });
    goto(url, { replaceState: true, noScroll: true });
  }
</script>

<svelte:head>
  <title>Assumptions | AgentZero Command Center</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
  <!-- Page Header -->
  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
    <div>
      <div class="flex items-center gap-3 mb-2">
        <div class="w-8 h-8 rounded-md bg-accent-500/10 flex items-center justify-center">
          <svg class="w-4 h-4 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
        </div>
        <h1 class="text-2xl font-semibold text-foreground">Assumptions Browser</h1>
      </div>
      <p class="text-sm text-muted">Explore and compare assumption packs across all runs.</p>
    </div>
    
    <div class="flex items-center gap-3">
      <span class="text-xs text-muted uppercase tracking-wider">View</span>
      <div class="flex rounded-md border border-border-subtle overflow-hidden">
        <button
          on:click={() => viewMode = 'table'}
          class="px-3 py-1.5 text-sm font-medium transition-colors
                 {viewMode === 'table'
                   ? 'bg-accent-500/10 text-accent-500'
                   : 'bg-surface text-muted hover:text-foreground'}"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>
        <button
          on:click={() => viewMode = 'cards'}
          class="px-3 py-1.5 text-sm font-medium transition-colors border-l border-border-subtle
                 {viewMode === 'cards'
                   ? 'bg-accent-500/10 text-accent-500'
                   : 'bg-surface text-muted hover:text-foreground'}"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
        </button>
      </div>
    </div>
  </div>

  {#if isLoading}
    <div class="card p-16 text-center">
      <div class="spinner mx-auto mb-4"></div>
      <p class="text-muted">Loading assumptions...</p>
    </div>
  {:else if error}
    <div class="card p-6 border-error-500/30">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-md bg-error-500/10 flex items-center justify-center">
          <svg class="w-4 h-4 text-error-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p class="font-medium text-error-500">Error Loading Assumptions</p>
          <p class="text-sm text-muted">{error}</p>
        </div>
      </div>
    </div>
  {:else}
    <div class="space-y-6">
      <!-- Assumption Packs -->
      <div class="card p-4">
        <h2 class="section-title">Assumption Packs</h2>
        <div class="flex flex-wrap gap-2">
          <button
            on:click={() => selectedPack = ''}
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-all
                   {selectedPack === ''
                     ? 'bg-accent-500/10 text-accent-500 ring-1 ring-accent-500/30'
                     : 'bg-surface-muted text-muted hover:text-foreground'}"
          >
            All Packs
            <span class="ml-1 font-mono text-xs opacity-75">({allAssumptions.length})</span>
          </button>
          {#each assumptionPacks as pack}
            <button
              on:click={() => selectedPack = pack.id}
              class="px-3 py-1.5 text-sm font-medium rounded-md transition-all
                     {selectedPack === pack.id
                       ? 'bg-accent-500/10 text-accent-500 ring-1 ring-accent-500/30'
                       : 'bg-surface-muted text-muted hover:text-foreground'}"
            >
              {pack.id}
              <span class="ml-1 font-mono text-xs opacity-75">({pack.runs.length})</span>
            </button>
          {/each}
        </div>

        {#if selectedPack}
          <div class="mt-4 pt-4 border-t border-border-subtle">
            <span class="text-xs text-muted uppercase tracking-wider">Linked Runs</span>
            <div class="flex flex-wrap gap-2 mt-2">
              {#each assumptionPacks.find(p => p.id === selectedPack)?.runs ?? [] as runId}
                <TraceabilityLink 
                  href={runUrl(runId)}
                  label={runId}
                  icon="arrow"
                  variant="inline"
                />
              {/each}
            </div>
          </div>
        {/if}
      </div>

      <!-- Filters -->
      <div class="card p-4">
        <AssumptionFilters 
          {regions} 
          {techs} 
          {params}
          on:filter={handleFilter}
        />
      </div>

      <!-- Results Count -->
      <div class="flex items-center justify-between">
        <p class="text-sm text-muted">
          Showing <span class="font-mono text-foreground">{filteredAssumptions.length}</span> of <span class="font-mono">{displayAssumptions.length}</span> assumptions
          {#if selectedPack}
            from pack <span class="font-mono text-accent-500">"{selectedPack}"</span>
          {/if}
        </p>
      </div>

      <!-- Results -->
      {#if viewMode === 'table'}
        <div class="card overflow-hidden">
          <AssumptionTable assumptions={filteredAssumptions} />
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each filteredAssumptions as assumption (assumption.param + assumption.region + assumption.tech + assumption.year + assumption.runs.join(','))}
            <AssumptionCard {assumption} />
          {/each}
        </div>
        {#if filteredAssumptions.length === 0}
          <div class="card">
            <div class="empty-state">
              <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              <p class="empty-state-title">No matching assumptions</p>
              <p class="empty-state-description">Try adjusting your filter criteria.</p>
            </div>
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>
