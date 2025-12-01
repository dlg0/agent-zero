<script lang="ts">
</script>

<svelte:head>
  <title>Scenarios | AgentZero Command Center</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  <!-- Page Header -->
  <div class="mb-8">
    <div class="flex items-center gap-3 mb-2">
      <div class="w-8 h-8 rounded-md bg-accent-500/10 flex items-center justify-center">
        <svg class="w-4 h-4 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      </div>
      <h1 class="text-2xl font-semibold text-foreground">Scenario Browser</h1>
    </div>
    <p class="text-sm text-muted">Explore and manage scenario configurations.</p>
  </div>

  <!-- Coming Soon State -->
  <div class="card">
    <div class="empty-state">
      <div class="w-16 h-16 rounded-full bg-accent-500/10 flex items-center justify-center mb-6">
        <svg class="w-8 h-8 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      </div>
      <p class="empty-state-title">Scenario Browser</p>
      <p class="empty-state-description mb-4">
        This feature is currently under development.
      </p>
      <span class="badge badge-accent">
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Coming Soon
      </span>
    </div>
  </div>
</div>
