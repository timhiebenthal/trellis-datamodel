import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import { nodes, dbtModels, entityDetailModal } from '$lib/stores';
import type { DbtModel } from '$lib/types';
import { updateModelSchema } from '$lib/api';

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

function setupUnboundEntityWithDraftOrigin() {
  nodes.set([{
    id: 'node-1',
    type: 'entity',
    position: { x: 0, y: 0 },
    data: {
      label: 'Appointment',
      entity_type: 'dimension',
      drafted_fields: [{
        name: 'appointment_id',
        datatype: 'text',
        description: 'Unique identifier',
        origin: 'DH1: CORE.T_DYN_APPOINTMENT.ACTIVITYID | DH2: CBUS_APPOINTMENT.APPOINTMENT_AID',
      }],
    } as any,
  }] as any);
  dbtModels.set([]);
  entityDetailModal.set({ open: true, entityId: 'node-1' });
}

/** Bound model + extra drafted row with a user-defined origin (merged export path). */
function setupBoundEntityWithDraftOrigin() {
  nodes.set([{
    id: 'node-1',
    type: 'entity',
    position: { x: 0, y: 0 },
    data: {
      label: 'Mixed Entity',
      dbt_model: 'model.proj.entity_x',
      drafted_fields: [{
        name: 'extra_col',
        datatype: 'text',
        description: 'Draft column',
        origin: 'LINEAGE:user_defined',
      }],
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
    vi.clearAllMocks();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    nodes.set([]);
    dbtModels.set([]);
    entityDetailModal.set({ open: false, entityId: null });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
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
    const materializeButtons = screen.getAllByTitle(/Write to.*schema.yml/i);
    expect(materializeButtons).toHaveLength(1);
  });

  it('shows editable origin input for draft rows', async () => {
    setupBoundEntityWithDraft();
    await renderModal();
    expect(screen.getByPlaceholderText('Origin')).toBeInTheDocument();
  });

  it('Copy as Markdown: unbound entity copies title, drafted origins, and relationships placeholder', async () => {
    setupUnboundEntityWithDraftOrigin();
    await renderModal();

    await fireEvent.click(screen.getByLabelText('Export options'));
    await fireEvent.click(screen.getByText('Copy as Markdown'));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
      const markdown = (navigator.clipboard.writeText as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
      expect(markdown).toContain('# Appointment');
      expect(markdown).toContain('## Attributes');
      expect(markdown).toContain('| Name | Type | Description | Origin |');
      expect(markdown).toContain(
        '| appointment_id | text | Unique identifier | DH1: CORE.T_DYN_APPOINTMENT.ACTIVITYID &#124; DH2: CBUS_APPOINTMENT.APPOINTMENT_AID |'
      );
      expect(markdown).toContain('## Relationships');
      expect(markdown).toContain('No relationships defined');
    });
  });

  it('Copy as Markdown: bound entity uses dbt model unique_id for materialized rows and preserves draft origin', async () => {
    setupBoundEntityWithDraftOrigin();
    await renderModal();

    await fireEvent.click(screen.getByLabelText('Export options'));
    await fireEvent.click(screen.getByText('Copy as Markdown'));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
      const markdown = (navigator.clipboard.writeText as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
      expect(markdown).toContain('# Mixed Entity');
      expect(markdown).toContain('| id | int |  | model.proj.entity_x |');
      expect(markdown).toContain('| created_at | timestamp |  | model.proj.entity_x |');
      expect(markdown).toContain('| extra_col | text | Draft column | LINEAGE:user_defined |');
    });
  });

  it('removes draft from list after materializing and shows SQL-gap warning', async () => {
    setupBoundEntityWithDraft();
    await renderModal();

    await fireEvent.click(screen.getByTitle(/Write to.*schema.yml/i));

    await waitFor(() => {
      expect(updateModelSchema).toHaveBeenCalled();
      expect(screen.queryByDisplayValue('pending_col')).not.toBeInTheDocument();
      expect(screen.getByText(/Column 'pending_col' added to schema\.yml/i)).toBeInTheDocument();
    });
  });
});
