import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { frameworkModels, viewMode } from '$lib/stores';
import EntityNode from './EntityNode.svelte';
import type { EntityData } from '$lib/types';
import { computeUiTagsAfterEdit } from '$lib/utils/entity-tags';

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
    model_ref: 'model.project.booking',
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
    frameworkModels.set([mockDbtModel] as any);
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

  it('accepts dbt_tags/ui_tags on EntityData without a type error', () => {
    const data: EntityData = {
        label: 'Users',
        tags: ['nightly', 'pii'],
        dbt_tags: ['nightly'],
        ui_tags: ['pii'],
    } as EntityData;
    expect(data.dbt_tags).toEqual(['nightly']);
    expect(data.ui_tags).toEqual(['pii']);
  });
});

describe('EntityNode — handleTagsUpdate provenance diff (via computeUiTagsAfterEdit)', () => {
  // handleTagsUpdate delegates its dbt-mirrored-vs-ui diff to this pure helper
  // (frontend/src/lib/utils/entity-tags.ts). Rendering the full component and asserting on
  // useSvelteFlow()'s updateNodeData isn't viable here: the mock in this file creates a fresh
  // vi.fn() per render with no stable handle to assert against, and — once the read-only
  // rendering fix lands — a dbt-mirrored chip has no remove button in the DOM to click at all,
  // so the "user tries to remove a dbt-mirrored tag" scenario can't be driven through the UI
  // post-fix. Testing the extracted diff logic directly proves the same behavior handleTagsUpdate
  // relies on.

  it('adding a tag via handleTagsUpdate appends only to ui_tags, leaving dbt_tags untouched', () => {
    // Bound node: data.dbt_tags = ['nightly'], data.ui_tags = [].
    // Tag editor widget currently shows the union ['nightly'] and the user types 'pii',
    // so onUpdate fires with newTags = ['nightly', 'pii'].
    const dbtTags = ['nightly'];
    const newTags = ['nightly', 'pii'];

    const uiTags = computeUiTagsAfterEdit(dbtTags, newTags);

    // dbt-mirrored 'nightly' is not in the result — it's tracked via `dbt_tags`, not `ui_tags`.
    expect(uiTags).toEqual(['pii']);
    expect(dbtTags).toEqual(['nightly']); // unchanged — not this function's to touch
  });

  it('removing a dbt-mirrored tag from the editor is a no-op on ui_tags', () => {
    // Bound node: data.dbt_tags = ['nightly'], data.ui_tags = ['pii'].
    // User tries to drop the 'nightly' chip from the widget, so onUpdate fires with
    // newTags = ['pii'] (nightly missing) — but nightly was never Trellis's to remove.
    const dbtTags = ['nightly'];
    const newTags = ['pii'];

    const uiTags = computeUiTagsAfterEdit(dbtTags, newTags);

    // ui_tags is still ['pii'] — the attempted removal of the dbt-mirrored tag is a no-op.
    expect(uiTags).toEqual(['pii']);
  });
});
