import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import LineageModal from './LineageModal.svelte';
import type { LineageResponse } from '$lib/types';

// SvelteFlow measures its container with ResizeObserver, which jsdom lacks.
class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
}

const ROOT_ONLY_LINEAGE: LineageResponse = {
    nodes: [],
    edges: [],
    metadata: {
        root_model_id: 'model.proj.dim_customer',
        level_counts: {},
        total_nodes: 0,
        total_edges: 0,
    },
};

const LINEAGE: LineageResponse = {
    nodes: [
        { id: 'model.proj.dim_customer', label: 'dim_customer', level: 0, isSource: false },
        { id: 'model.proj.clean_customer', label: 'clean_customer', level: 1, isSource: false },
        { id: 'source.proj.crm.customers', label: 'customers', level: 2, isSource: true, sourceName: 'crm' },
    ],
    edges: [
        { source: 'model.proj.clean_customer', target: 'model.proj.dim_customer', level: 1 },
        { source: 'source.proj.crm.customers', target: 'model.proj.clean_customer', level: 2 },
    ],
    metadata: {
        root_model_id: 'model.proj.dim_customer',
        level_counts: { 0: 1, 1: 1, 2: 1 },
        total_nodes: 3,
        total_edges: 2,
    },
};

function respondWith(status: number, body?: unknown) {
    return vi.fn().mockResolvedValue({
        ok: status >= 200 && status < 300,
        status,
        json: vi.fn().mockResolvedValue(body),
    });
}

describe('LineageModal', () => {
    beforeEach(() => {
        vi.stubGlobal('ResizeObserver', ResizeObserverStub);
        vi.stubGlobal(
            'matchMedia',
            vi.fn().mockReturnValue({
                matches: false,
                addEventListener: () => {},
                removeEventListener: () => {},
            }),
        );
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('renders nothing and fetches nothing when closed', () => {
        const fetchMock = respondWith(200, LINEAGE);
        vi.stubGlobal('fetch', fetchMock);

        render(LineageModal, { open: false, modelId: 'model.proj.dim_customer', onClose: vi.fn() });

        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it('requests lineage for the model and shows the title with the model id', async () => {
        const fetchMock = respondWith(200, LINEAGE);
        vi.stubGlobal('fetch', fetchMock);

        render(LineageModal, { open: true, modelId: 'model.proj.dim_customer', onClose: vi.fn() });

        expect(screen.getByRole('dialog', { name: /upstream lineage/i })).toBeInTheDocument();
        expect(screen.getByText('model.proj.dim_customer')).toBeInTheDocument();
        await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
        expect(String(fetchMock.mock.calls[0][0])).toContain(
            `/lineage/${encodeURIComponent('model.proj.dim_customer')}`,
        );
    });

    it('shows a loading indicator while lineage is being generated', async () => {
        vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})));

        render(LineageModal, { open: true, modelId: 'model.proj.dim_customer', onClose: vi.fn() });

        expect(await screen.findByText('Generating lineage...')).toBeInTheDocument();
    });

    it('renders the upstream models and sources of the lineage graph', async () => {
        vi.stubGlobal('fetch', respondWith(200, LINEAGE));

        render(LineageModal, { open: true, modelId: 'model.proj.dim_customer', onClose: vi.fn() });

        expect(await screen.findByText('clean_customer', { selector: 'span' })).toBeInTheDocument();
        expect(await screen.findByText('dim_customer', { selector: 'span' })).toBeInTheDocument();
        expect(await screen.findByText('customers', { selector: 'span' })).toBeInTheDocument();
        expect(screen.queryByText('Generating lineage...')).not.toBeInTheDocument();
    });

    it('explains when a model has no upstream dependencies', async () => {
        vi.stubGlobal('fetch', respondWith(200, ROOT_ONLY_LINEAGE));

        render(LineageModal, { open: true, modelId: 'model.proj.dim_customer', onClose: vi.fn() });

        expect(
            await screen.findByText('No upstream dependencies found for this model.'),
        ).toBeInTheDocument();
    });

    it('shows an error when the model is unknown', async () => {
        vi.stubGlobal('fetch', respondWith(404));

        render(LineageModal, { open: true, modelId: 'model.proj.missing', onClose: vi.fn() });

        expect(
            await screen.findByText('Model not found or lineage could not be generated.'),
        ).toBeInTheDocument();
    });

    it('Retry reloads the lineage after a failure', async () => {
        const fetchMock = vi
            .fn()
            .mockResolvedValueOnce({ ok: false, status: 404, json: vi.fn() })
            .mockResolvedValue({ ok: true, status: 200, json: vi.fn().mockResolvedValue(LINEAGE) });
        vi.stubGlobal('fetch', fetchMock);

        render(LineageModal, { open: true, modelId: 'model.proj.dim_customer', onClose: vi.fn() });

        await fireEvent.click(await screen.findByRole('button', { name: 'Retry' }));

        expect(await screen.findByText('clean_customer', { selector: 'span' })).toBeInTheDocument();
        expect(screen.queryByText(/could not be generated/)).not.toBeInTheDocument();
        expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it('calls onClose from the Close button', async () => {
        vi.stubGlobal('fetch', respondWith(200, LINEAGE));
        const onClose = vi.fn();

        render(LineageModal, { open: true, modelId: 'model.proj.dim_customer', onClose });

        await fireEvent.click(screen.getByRole('button', { name: 'Close' }));
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
