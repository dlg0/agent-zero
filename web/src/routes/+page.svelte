<script lang="ts">
  import { base } from '$app/paths';
</script>

<svelte:head>
  <title>AgentZero — AI Agent Command Center</title>
</svelte:head>

<div class="min-h-[calc(100vh-200px)] flex items-center">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 w-full">
    
    <!-- Hero Section -->
    <div class="text-center mb-16">
      <!-- Status Badge -->
      <div class="inline-flex items-center gap-2 mb-8">
        <span class="badge badge-accent">
          <span class="status-dot status-dot-active"></span>
          Systems Online
        </span>
      </div>

      <!-- Main Title -->
      <h1 class="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground tracking-tight mb-6">
        Agent<span class="text-accent-500">Zero</span>
      </h1>
      
      <!-- Tagline -->
      <p class="text-xl sm:text-2xl text-muted mb-4 max-w-2xl mx-auto font-light">
        AI Agent Orchestration Platform
      </p>
      <p class="text-muted max-w-xl mx-auto leading-relaxed">
        Define tools, build autonomous agents, and monitor execution in real-time.
        Enterprise-grade reliability for mission-critical AI workflows.
      </p>
    </div>

    <!-- Key Metrics Dashboard -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
      <div class="data-panel text-center">
        <div class="metric-value text-accent-500">99.9%</div>
        <div class="metric-label mt-1">Uptime SLA</div>
      </div>
      <div class="data-panel text-center">
        <div class="metric-value text-foreground">&lt; 50ms</div>
        <div class="metric-label mt-1">Response Time</div>
      </div>
      <div class="data-panel text-center">
        <div class="metric-value text-foreground">256-bit</div>
        <div class="metric-label mt-1">Encryption</div>
      </div>
      <div class="data-panel text-center">
        <div class="metric-value text-foreground">SOC 2</div>
        <div class="metric-label mt-1">Compliant</div>
      </div>
    </div>

    <!-- Feature Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
      <div class="card p-6">
        <div class="w-10 h-10 rounded-md bg-accent-500/10 flex items-center justify-center mb-4">
          <svg class="w-5 h-5 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-foreground mb-2">Tool Framework</h3>
        <p class="text-sm text-muted leading-relaxed">
          Define custom tools with JSON schemas. Full type safety, validation, and automatic documentation generation.
        </p>
        <div class="mt-4 pt-4 border-t border-border-subtle">
          <span class="badge badge-default">Production Ready</span>
        </div>
      </div>

      <div class="card p-6">
        <div class="w-10 h-10 rounded-md bg-accent-500/10 flex items-center justify-center mb-4">
          <svg class="w-5 h-5 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-foreground mb-2">Run Analytics</h3>
        <p class="text-sm text-muted leading-relaxed">
          Deep execution traces, performance metrics, and decision auditing. Full transparency into agent reasoning.
        </p>
        <div class="mt-4 pt-4 border-t border-border-subtle">
          <span class="badge badge-success">
            <span class="status-dot status-dot-active"></span>
            Real-time
          </span>
        </div>
      </div>

      <div class="card p-6">
        <div class="w-10 h-10 rounded-md bg-accent-500/10 flex items-center justify-center mb-4">
          <svg class="w-5 h-5 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-foreground mb-2">Multi-Provider</h3>
        <p class="text-sm text-muted leading-relaxed">
          OpenAI, Anthropic, Azure, and more. Switch providers without code changes. Automatic failover support.
        </p>
        <div class="mt-4 pt-4 border-t border-border-subtle">
          <span class="badge badge-default">Enterprise</span>
        </div>
      </div>
    </div>

    <!-- Call to Action -->
    <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
      <a href="{base}/runs" class="btn-primary">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        Open Command Center
      </a>
      <a
        href="https://github.com/dlg0/agent-zero"
        target="_blank"
        rel="noopener noreferrer"
        class="btn-secondary"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>
        </svg>
        View Source
      </a>
    </div>

    <!-- Trust Indicators -->
    <div class="mt-20 pt-8 border-t border-border-subtle">
      <p class="text-center text-xs text-muted uppercase tracking-wider mb-6">Trusted Architecture</p>
      <div class="flex flex-wrap justify-center items-center gap-8 text-muted">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span class="text-sm">End-to-end Encryption</span>
        </div>
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span class="text-sm">Audit Logging</span>
        </div>
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span class="text-sm">Role-based Access</span>
        </div>
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span class="text-sm">Reproducible Runs</span>
        </div>
      </div>
    </div>

  </div>
</div>
