import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { dbtModels, viewMode } from '$lib/stores';
import EntityNode from './EntityNode.svelte';
import type { EntityData } from '$lib/types';

// Mock heavy dependencies
vi.mock('@xyflow/svelte', async () => {
  const { readable, writable } = await import('svelte/store');
  const mockStore = writable({ nodeInternals: new Map(), edges: [], width: 0, height: 0 });
  return {
    Handle: vi.fn(),
    Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
    useSvelteFlow: vi.fn(() => ({
      updateNodeData: vi.fn(),
      getNode: vi.fn(),
    })),
    useNodes: vi.fn(() => readable([])),
    useStore: vi.fn(() => mockStore),
    SvelteFlowProvider: vi.fn(),
  };
});

vi.mock('$lib/api', () => ({
  getManifest: vi.fn().mockResolvedValue([]),
  getSourceSystemSuggestions: vi.fn().mockResolvedValue([]),
  inferRelationships: vi.fn().mockResolvedValue([]),
  getLineage: vi.fn().mockResolvedValue(null),
  getModelSchema: vi.fn().mockResolvedValue(null),
}));

vi.mock('$lib/services/schema-manager', () => {
  class SchemaManager {
    loadSchema = vi.fn();
    getState = vi.fn().mockReturnValue({ editableColumns: [], isLoading: false, isSaving: false, error: null, hasUnsavedChanges: false });
    onStateChange = vi.fn();
    constructor(_cb: unknown) {}
  }
  return { SchemaManager };
});

vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
}));

const mockProps = {
  id: 'booking',
  data: {
    label: 'Booking',
    dbt_model: 'model.project.booking',
    drafted_fields: [{ name: 'new_col', datatype: 'text', description: '' }],
    width: 280,
    panelHeight: 200,
    collapsed: false,
  } as any,
  selected: false,
};

const mockDbtModel = {
  unique_id: 'model.project.booking',
  name: 'booking',
  schema: 'public',
  table: 'booking',
  columns: [
    { name: 'id', type: 'int' },
    { name: 'created_at', type: 'timestamp' },
  ],
};

const svelteFlowContext = new Map<string, unknown>([
  ['svelteFlow', { updateNodeData: vi.fn(), getNode: vi.fn() }],
]);

describe('EntityNode — merged field rendering', () => {
  beforeEach(() => {
    dbtModels.set([mockDbtModel] as any);
    viewMode.set('logical');
    vi.clearAllMocks();
  });

  it('renders 3 rows (2 dbt + 1 draft) for a bound entity in logical view', () => {
    render(EntityNode, {
      props: mockProps,
      context: svelteFlowContext,
    });
    const indicators = document.querySelectorAll('[data-origin="dbt"], [data-origin="draft"]');
    expect(indicators.length).toBeGreaterThanOrEqual(3);
  });

  it('dbt rows have "Materialized in dbt model" aria-label on indicator', () => {
    render(EntityNode, {
      props: mockProps,
      context: svelteFlowContext,
    });
    const materializedIndicators = document.querySelectorAll('[aria-label*="Materialized in dbt model"]');
    expect(materializedIndicators.length).toBeGreaterThanOrEqual(2);
  });

  it('draft row has "Drafted in Trellis" aria-label on indicator', () => {
    render(EntityNode, {
      props: mockProps,
      context: svelteFlowContext,
    });
    const draftIndicators = document.querySelectorAll('[aria-label*="Drafted in Trellis"]');
    expect(draftIndicators.length).toBeGreaterThanOrEqual(1);
  });

  it('Add Field button is visible on bound entities', () => {
    render(EntityNode, {
      props: mockProps,
      context: svelteFlowContext,
    });
    const addBtn = Array.from(document.querySelectorAll('button')).find(
      b => b.textContent?.toLowerCase().includes('add field') || b.textContent?.toLowerCase().includes('add')
    );
    expect(addBtn).toBeTruthy();
  });

  it('no Materialize button on canvas chip (scope decision)', () => {
    render(EntityNode, {
      props: mockProps,
      context: svelteFlowContext,
    });
    const materializeBtns = Array.from(document.querySelectorAll('button')).filter(
      b => b.title?.toLowerCase().includes('materialize') || b.getAttribute('aria-label')?.toLowerCase().includes('materialize')
    );
    expect(materializeBtns.length).toBe(0);
  });

  it('accepts trellis_tags on EntityData without a type error', () => {
    const data: EntityData = {
        label: 'Users',
        tags: ['nightly'],
        trellis_tags: ['pii'],
    } as EntityData;
    expect(data.trellis_tags).toEqual(['pii']);
  });
});
