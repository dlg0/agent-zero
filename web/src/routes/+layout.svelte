<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';
  import { onMount, type Snippet } from 'svelte';

  interface Props {
    children: Snippet;
  }
  
  let { children }: Props = $props();

  const navItems = [
    { href: '/runs', label: 'Runs', icon: 'terminal' },
    { href: '/assumptions', label: 'Assumptions', icon: 'database' },
    { href: '/scenarios', label: 'Scenarios', icon: 'layers' },
    { href: '/compare', label: 'Compare', icon: 'chart' }
  ];

  let currentPath = $derived($page.url.pathname);
  let scrolled = $state(false);
  let mobileMenuOpen = $state(false);

  type Theme = 'light' | 'dark';
  let theme: Theme = $state('dark');

  function applyTheme(value: Theme) {
    theme = value;

    if (typeof document === 'undefined') return;

    const root = document.documentElement;
    if (value === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    try {
      localStorage.setItem('theme', value);
    } catch {
      // ignore storage errors
    }
  }

  function toggleTheme() {
    applyTheme(theme === 'dark' ? 'light' : 'dark');
  }

  onMount(() => {
    try {
      const stored = localStorage.getItem('theme');
      if (stored === 'light' || stored === 'dark') {
        applyTheme(stored);
        return;
      }
    } catch {
      // ignore storage errors
    }

    // Default to dark for professional command center look
    applyTheme('dark');

    const handleScroll = () => {
      scrolled = window.scrollY > 10;
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  });
</script>

<div class="min-h-screen flex flex-col">
  <!-- Command Bar — Authority accent -->
  <div class="command-bar"></div>

  <!-- Header -->
  <header
    class="sticky top-0 z-50 transition-all duration-200 {scrolled ? 'glass shadow-sm' : 'bg-nav border-b border-border-subtle'}"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex h-14 items-center justify-between gap-6">
        <!-- Logo -->
        <a href="/" class="flex items-center gap-3 group">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-md bg-accent-500 flex items-center justify-center shadow-sm">
              <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span class="text-lg font-semibold tracking-tight text-foreground">
              AgentZero
            </span>
          </div>
          <span class="hidden sm:inline-flex badge badge-accent">
            <span class="status-dot status-dot-active"></span>
            Command Center
          </span>
        </a>

        <!-- Desktop Nav -->
        <nav class="hidden md:flex items-center gap-1">
          {#each navItems as item}
            {@const isActive = currentPath.startsWith(item.href)}
            <a
              href={item.href}
              class="nav-link {isActive ? 'nav-link-active' : ''}"
            >
              <span class="flex items-center gap-2">
                {#if item.icon === 'terminal'}
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                {:else if item.icon === 'database'}
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                {:else if item.icon === 'layers'}
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                {:else if item.icon === 'chart'}
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                {/if}
                {item.label}
              </span>
            </a>
          {/each}
        </nav>

        <!-- Right side actions -->
        <div class="flex items-center gap-2">
          <!-- Theme toggle -->
          <button
            type="button"
            class="btn-ghost h-9 w-9 p-0"
            onclick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          >
            {#if theme === 'dark'}
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
              </svg>
            {:else}
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            {/if}
          </button>

          <!-- GitHub link -->
          <a
            href="https://github.com/dlg0/agent-zero"
            target="_blank"
            rel="noopener noreferrer"
            class="hidden sm:inline-flex btn-ghost h-9 w-9 p-0"
            aria-label="View on GitHub"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>
            </svg>
          </a>

          <!-- Mobile menu button -->
          <button
            type="button"
            class="md:hidden btn-ghost h-9 w-9 p-0"
            aria-label="Open menu"
            onclick={() => mobileMenuOpen = !mobileMenuOpen}
          >
            {#if mobileMenuOpen}
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            {:else}
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            {/if}
          </button>
        </div>
      </div>

      <!-- Mobile menu -->
      {#if mobileMenuOpen}
        <div class="md:hidden py-4 border-t border-border-subtle fade-in">
          <nav class="flex flex-col gap-1">
            {#each navItems as item}
              {@const isActive = currentPath.startsWith(item.href)}
              <a
                href={item.href}
                onclick={() => mobileMenuOpen = false}
                class="nav-link {isActive ? 'nav-link-active' : ''}"
              >
                {item.label}
              </a>
            {/each}
          </nav>
        </div>
      {/if}
    </div>
  </header>

  <!-- Page content -->
  <main class="flex-1">
    {@render children()}
  </main>

  <!-- Footer -->
  <footer class="mt-auto border-t border-border-subtle bg-footer">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <div class="w-6 h-6 rounded bg-accent-500/20 flex items-center justify-center">
            <svg class="w-3 h-3 text-accent-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span class="text-sm text-muted">
            AgentZero · AI Agent Command Center
          </span>
        </div>
        <div class="flex items-center gap-6">
          <a href="https://github.com/dlg0/agent-zero" class="text-muted hover:text-foreground transition-colors text-sm">
            GitHub
          </a>
          <span class="text-border-subtle">·</span>
          <span class="text-xs text-muted font-mono">
            v0.1.0
          </span>
        </div>
      </div>
    </div>
  </footer>
</div>
