/**
 * Page-level wiring for the metric tree: load, edit, autosave.
 *
 * Svelte Flow is swapped for a recorder so the test can read the nodes the canvas
 * is given. That is what makes "a save does not remount the canvas or reset node
 * positions" assertable: the recorder counts instantiations and the props object
 * stays readable after every state change.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';

const flow = vi.hoisted(() => ({
    instances: 0,
    props: null as Record<string, any> | null,
}));

const api = vi.hoisted(() => ({
    getConfigInfo: vi.fn(),
    getMetricTree: vi.fn(),
    getDataModel: vi.fn(),
    saveMetricTree: vi.fn(),
}));

vi.mock('$lib/api', () => api);

vi.mock('@xyflow/svelte', () => ({
    SvelteFlow: (_anchor: unknown, props: Record<string, any>) => {
        flow.instances += 1;
        flow.props = props;
    },
    Controls: () => {},
    Background: () => {},
    BackgroundVariant: { Dots: 'dots', Lines: 'lines', Cross: 'cross' },
    Handle: () => {},
    Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
    MarkerType: { Arrow: 'arrow', ArrowClosed: 'arrowclosed' },
    BaseEdge: () => {},
    getBezierPath: () => ['M0,0', 0, 0, 0, 0],
    useSvelteFlow: () => ({ updateNodeData: vi.fn(), getNode: vi.fn() }),
}));

import MetricsTreePage from './+page.svelte';

function nodePositions() {
    const nodes = (flow.props?.nodes ?? []) as Array<{ id: string; position: { x: number; y: number } }>;
    return nodes.map((node) => ({ id: node.id, position: { ...node.position } }));
}

beforeEach(() => {
    flow.instances = 0;
    flow.props = null;

    api.getConfigInfo.mockResolvedValue({ metrics_enabled: true });
    api.getMetricTree.mockResolvedValue({
        version: 0.1,
        metrics: [
            {
                id: 'revenue',
                label: 'Revenue',
                description: 'Booked revenue.',
                expression: 'sum(amount)',
                dataset_ref: 'fct__order',
                position: { x: 10, y: 20 },
            },
            { id: 'orders', label: 'Orders', expression: 'count(*)' },
        ],
        influences: [{ effect: 'revenue', drivers: ['orders'] }],
        catalog: [
            { name: 'avg_price', dataset: 'fct__order', entity_id: 'fct__order', bindable: true },
        ],
    });
    api.getDataModel.mockResolvedValue({
        version: 0.1,
        entities: [{ id: 'fct__order', label: 'Order', position: { x: 0, y: 0 } }],
        relationships: [],
    });
    api.saveMetricTree.mockResolvedValue({ status: 'success', warnings: [] });
});

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe('metrics-tree page', () => {
    it('passes the loaded document to the canvas with its stored positions', async () => {
        render(MetricsTreePage);

        await waitFor(() => expect(flow.props).not.toBeNull());

        expect(nodePositions()).toEqual([
            { id: 'revenue', position: { x: 10, y: 20 } },
            { id: 'orders', position: expect.any(Object) },
        ]);
        expect(nodePositions()[1].position).not.toEqual({ x: 0, y: 0 });
    });

    it('saves an edit without remounting the canvas or moving a node', async () => {
        const { container } = render(MetricsTreePage);
        await waitFor(() => expect(flow.props).not.toBeNull());

        const before = nodePositions();

        // Open the draft in the inspector and change its label.
        await fireEvent.click(
            container.querySelector('[data-testid="metric-sidebar-select"]') as HTMLElement,
        );
        const labelInput = document.querySelector(
            '[data-testid="metric-field-label"]',
        ) as HTMLInputElement | null;
        expect(labelInput).not.toBeNull();

        await fireEvent.input(labelInput!, { target: { value: 'Booked revenue' } });

        await waitFor(() => expect(api.saveMetricTree).toHaveBeenCalledTimes(1), { timeout: 2000 });

        const payload = api.saveMetricTree.mock.calls[0][0];
        expect(payload.metrics[0].label).toBe('Booked revenue');
        expect(payload.metrics[0].position).toEqual({ x: 10, y: 20 });

        // The canvas instance is the same one, still at the same coordinates.
        expect(flow.instances).toBe(1);
        expect(nodePositions()).toEqual(before);
    });

    it('holds the save back while a new draft has no expression', async () => {
        const { container } = render(MetricsTreePage);
        await waitFor(() => expect(flow.props).not.toBeNull());

        await fireEvent.click(
            container.querySelector('[data-testid="metric-sidebar-add"]') as HTMLElement,
        );

        await new Promise((resolve) => setTimeout(resolve, 600));

        expect(api.saveMetricTree).not.toHaveBeenCalled();
        expect(container.textContent).toContain('Auto-save paused');
        expect(nodePositions()).toHaveLength(3);
    });

    it('writes a catalog metric as a binding with no expression', async () => {
        const { container } = render(MetricsTreePage);
        await waitFor(() => expect(flow.props).not.toBeNull());

        await fireEvent.click(
            container.querySelector('[data-testid="metric-sidebar-catalog-add"]') as HTMLElement,
        );

        await waitFor(() => expect(api.saveMetricTree).toHaveBeenCalledTimes(1), { timeout: 2000 });

        const added = api.saveMetricTree.mock.calls[0][0].metrics.find(
            (metric: { id: string }) => metric.id === 'avg_price',
        );
        expect(added).toEqual({
            id: 'avg_price',
            label: 'Avg price',
            binding: { dataset: 'fct__order', name: 'avg_price' },
        });
    });
});
