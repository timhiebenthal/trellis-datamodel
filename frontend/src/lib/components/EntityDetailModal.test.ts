import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import { nodes, dbtModels, entityDetailModal } from '$lib/stores';
import type { DbtModel } from '$lib/types';

// Mock heavy API/navigation deps so they don't crash in jsdom
vi.mock('$lib/api', () => ({
  getSourceSystemSuggestions: vi.fn().mockResolvedValue([]),
  getBusinessEventProcesses: vi.fn().mockResolvedValue([]),
  updateModelSchema: vi.fn().mockResolvedValue({ model_name: 'x', description: '', columns: [], tags: [], file_path: '' }),
  getManifest: vi.fn().mockResolvedValue([]),
}));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

const mockDbtModel: DbtModel = {
  unique_id: 'model.proj.entity_x',
  name: 'entity_x',
  schema: 'public',
  table: 'entity_x',
  columns: [
    { name: 'id', type: 'int' },
    { name: 'created_at', type: 'timestamp' },
  ],
};

function setupBoundEntityWithDraft() {
  nodes.set([{
    id: 'node-1',
    type: 'entity',
    position: { x: 0, y: 0 },
    data: {
      label: 'Entity X',
      dbt_model: 'model.proj.entity_x',
      drafted_fields: [{ name: 'pending_col', datatype: 'text' }],
    } as any,
  }] as any);
  dbtModels.set([mockDbtModel]);
  entityDetailModal.set({ open: true, entityId: 'node-1' });
}

async function renderModal() {
  // Dynamically import to ensure mocks are hoisted
  const { default: EntityDetailModal } = await import('./EntityDetailModal.svelte');
  return render(EntityDetailModal, {
    context: new Map([['autoSaveService', { current: null }]]),
  });
}

describe('EntityDetailModal — merged dbt+draft fields', () => {
  beforeEach(() => {
    nodes.set([]);
    dbtModels.set([]);
    entityDetailModal.set({ open: false, entityId: null });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders 3 rows for 2 dbt columns + 1 draft on a bound entity', async () => {
    setupBoundEntityWithDraft();
    await renderModal();
    const materializedIndicators = screen.getAllByLabelText(/Materialized in dbt model/i);
    expect(materializedIndicators).toHaveLength(2);
    const draftIndicators = screen.getAllByLabelText(/Drafted in Trellis/i);
    expect(draftIndicators).toHaveLength(1);
  });

  it('shows Add Attribute button for bound entities', async () => {
    setupBoundEntityWithDraft();
    await renderModal();
    expect(screen.getByText(/Add Attribute/i)).toBeInTheDocument();
  });

  it('has readonly name input for dbt rows and editable for draft rows', async () => {
    setupBoundEntityWithDraft();
    await renderModal();
    // Find all name inputs
    const nameInputs = screen.getAllByPlaceholderText('attribute_name');
    // dbt row inputs should be readonly
    const readonlyInputs = nameInputs.filter(el => el.hasAttribute('readonly'));
    expect(readonlyInputs).toHaveLength(2);
    // draft row input should be editable
    const editableInputs = nameInputs.filter(el => !el.hasAttribute('readonly'));
    expect(editableInputs).toHaveLength(1);
  });

  it('shows Materialize button on draft rows but not on dbt rows', async () => {
    setupBoundEntityWithDraft();
    await renderModal();
    const materializeButtons = screen.getAllByTitle(/Materialize this row into.*schema\.yml/i);
    expect(materializeButtons).toHaveLength(1);
  });

  it('shows editable origin input for draft rows', async () => {
    setupBoundEntityWithDraft();
    await renderModal();
    expect(screen.getByPlaceholderText('Origin')).toBeInTheDocument();
  });
});
