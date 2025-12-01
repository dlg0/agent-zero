import { describe, it, expect } from 'vitest';
import type {
  WebBundle,
  Manifest,
  Summary,
  Timeseries,
  Agents,
  AgentTraces,
  AssumptionsUsed,
  Drivers
} from '$lib/types';

import manifestJson from './fixtures/web_bundle/manifest.json';
import summaryJson from './fixtures/web_bundle/summary.json';
import timeseriesJson from './fixtures/web_bundle/timeseries.json';
import agentsJson from './fixtures/web_bundle/agents.json';
import agentTracesJson from './fixtures/web_bundle/agent_traces.json';
import assumptionsUsedJson from './fixtures/web_bundle/assumptions_used.json';
import driversJson from './fixtures/web_bundle/drivers.json';

const manifest = manifestJson as Manifest;
const summary = summaryJson as Summary;
const timeseries = timeseriesJson as Timeseries;
const agents = agentsJson as Agents;
const agent_traces = agentTracesJson as AgentTraces;
const assumptions_used = assumptionsUsedJson as AssumptionsUsed;
const drivers = driversJson as Drivers;

describe('Web bundle type contracts', () => {
  it('manifest matches Manifest type', () => {
    expect(manifest.run_id).toBeDefined();
    expect(manifest.years.start).toBeDefined();
    expect(manifest.years.end).toBeDefined();
  });

  it('summary matches Summary type', () => {
    expect(summary.run_id).toBeDefined();
  });

  it('timeseries matches Timeseries type', () => {
    expect(timeseries.length).toBeGreaterThan(0);
    expect(timeseries[0].year).toBeDefined();
  });

  it('agents matches Agents type', () => {
    expect(agents.length).toBeGreaterThan(0);
    expect(agents[0].agent_id).toBeDefined();
  });

  it('agent_traces matches AgentTraces type', () => {
    expect(agent_traces.length).toBeGreaterThan(0);
    expect(agent_traces[0].action).toBeDefined();
  });

  it('assumptions_used matches AssumptionsUsed type', () => {
    expect(assumptions_used.length).toBeGreaterThan(0);
    expect(assumptions_used[0].param).toBeDefined();
  });

  it('drivers matches Drivers type', () => {
    expect(drivers.length).toBeGreaterThan(0);
    expect(drivers[0].factor).toBeDefined();
  });

  it('full WebBundle can be constructed from fixtures', () => {
    const bundle: WebBundle = {
      manifest,
      summary,
      timeseries,
      agents,
      agent_traces,
      assumptions_used,
      drivers
    };
    expect(bundle.manifest.run_id).toBe('test-run-001');
  });
});
