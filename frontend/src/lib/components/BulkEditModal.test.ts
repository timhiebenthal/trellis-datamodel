import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent, within } from '@testing-library/svelte';
import { get } from 'svelte/store';
import type { Node } from '@xyflow/svelte';
import BulkEditModal from './BulkEditModal.svelte';
import { bulkEditModal, entitySelection, nodes } from '$lib/stores';

function entityNode(id: string, label: string, data: Record<string, unknown> = {}): Node {
    return {
        id,
        type: 'entity',
        position: { x: 0, y: 0 },
        data: { label, ...data },
    };
}

function seed(selectedEntityIds: string[]) {
    nodes.set([
        entityNode('customer', 'Customer', { domain: 'Sales', tags: ['pii', 'core'] }),
        entityNode('order', 'Order', { domain: 'Sales', tags: ['core'] }),
        entityNode('warehouse', 'Warehouse', { domain: 'Operations', tags: ['internal'] }),
    ]);
    bulkEditModal.set({ open: true, selectedEntityIds });
    entitySelection.set(new Set(selectedEntityIds));
}

function nodeData(id: string): Record<string, any> {
    return get(nodes).find((n) => n.id === id)!.data as Record<string, any>;
}

describe('BulkEditModal', () => {
    beforeEach(() => {
        nodes.set([]);
        bulkEditModal.set({ open: false, selectedEntityIds: [] });
        entitySelection.set(new Set());
    });

    afterEach(() => {
        cleanup();
    });

    it('renders nothing when closed', () => {
        seed(['customer']);
        render(BulkEditModal, { open: false, onClose: vi.fn() });

        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('lists the selected entities and their count', () => {
        seed(['customer', 'order']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        expect(screen.getByRole('dialog', { name: 'Bulk Edit Entities' })).toBeInTheDocument();
        expect(screen.getByText('2 entities selected')).toBeInTheDocument();
        expect(screen.getByText('Customer')).toBeInTheDocument();
        expect(screen.getByText('Order')).toBeInTheDocument();
        expect(screen.queryByText('Warehouse')).not.toBeInTheDocument();
    });

    it('uses the singular for a single selected entity', () => {
        seed(['customer']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        expect(screen.getByText('1 entity selected')).toBeInTheDocument();
    });

    it('keeps Apply Changes disabled until an operation is chosen', async () => {
        seed(['customer', 'order']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        const apply = screen.getByRole('button', { name: /apply changes/i });
        expect(apply).toBeDisabled();

        await fireEvent.change(screen.getByLabelText(/add domain/i), { target: { value: 'Operations' } });
        expect(apply).toBeEnabled();
    });

    it('offers every domain on the canvas, not just those of the selection', () => {
        seed(['customer']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        const select = screen.getByLabelText(/add domain/i);
        const options = Array.from(select.querySelectorAll('option')).map((o) => o.textContent);
        expect(options).toEqual(['— No change —', 'Operations', 'Sales']);
    });

    it('only offers removal of tags common to all selected entities', () => {
        seed(['customer', 'order']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        // "core" is on both; "pii" only on Customer.
        const removeSection = screen.getByText('Common tags:').parentElement!;
        expect(removeSection).toHaveTextContent('core');
        expect(removeSection).not.toHaveTextContent('pii');
    });

    it('says there are no common tags when the selection shares none', () => {
        seed(['customer', 'warehouse']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        expect(screen.getByText('No common tags')).toBeInTheDocument();
    });

    it('applies domain and new tag to all selected entities, leaves others alone, clears selection and closes', async () => {
        seed(['customer', 'order']);
        const onClose = vi.fn();
        render(BulkEditModal, { open: true, onClose });

        await fireEvent.change(screen.getByLabelText(/add domain/i), { target: { value: 'Operations' } });
        await fireEvent.input(screen.getByPlaceholderText('Type new tag...'), { target: { value: 'reviewed' } });
        await fireEvent.click(screen.getByRole('button', { name: /^add$/i }));
        expect(screen.getByText('Will add:')).toBeInTheDocument();

        await fireEvent.click(screen.getByRole('button', { name: /apply changes/i }));

        expect(nodeData('customer').domain).toBe('Operations');
        expect(nodeData('order').domain).toBe('Operations');
        expect(nodeData('customer').tags).toContain('reviewed');
        expect(nodeData('order').tags).toContain('reviewed');
        expect(nodeData('customer').tags).toContain('pii');
        // Unselected entity is untouched
        expect(nodeData('warehouse').domain).toBe('Operations');
        expect(nodeData('warehouse').tags).toEqual(['internal']);

        expect(get(entitySelection).size).toBe(0);
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('removes a selected common tag from every selected entity', async () => {
        seed(['customer', 'order']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        // "core" is also listed under "Add Tags > Select existing", so scope to the removal section.
        const removeSection = screen.getByText('Common tags:').parentElement!;
        await fireEvent.click(within(removeSection).getByRole('button', { name: 'core' }));
        expect(screen.getByText('Will remove:')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: /apply changes/i }));

        expect(nodeData('customer').tags).toEqual(['pii']);
        expect(nodeData('order').tags ?? []).toEqual([]);
    });

    it('does not add a blank tag', async () => {
        seed(['customer']);
        render(BulkEditModal, { open: true, onClose: vi.fn() });

        await fireEvent.input(screen.getByPlaceholderText('Type new tag...'), { target: { value: '   ' } });
        expect(screen.getByRole('button', { name: /^add$/i })).toBeDisabled();
    });

    it('Cancel closes without changing anything', async () => {
        seed(['customer', 'order']);
        const onClose = vi.fn();
        render(BulkEditModal, { open: true, onClose });

        await fireEvent.change(screen.getByLabelText(/add domain/i), { target: { value: 'Operations' } });
        await fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

        expect(onClose).toHaveBeenCalledTimes(1);
        expect(nodeData('customer').domain).toBe('Sales');
        expect(get(entitySelection).size).toBe(2);
    });

    it('Escape closes the dialog', async () => {
        seed(['customer']);
        const onClose = vi.fn();
        render(BulkEditModal, { open: true, onClose });

        await fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
