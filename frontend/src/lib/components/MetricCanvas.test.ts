import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
import type { MetricEntry, MetricInfluence } from '$lib/types';

/**
 * Svelte Flow needs a real DOM with layout, so the canvas test swaps it for a
 * recorder and asserts on the nodes and edges the component hands it. That is the
 * contract the page cares about: one node per metric, one edge per driver.
 */
const captured = vi.hoisted(() => ({ flows: [] as Array<Record<string, any>> }));

vi.mock('@xyflow/svelte', () => ({
    SvelteFlow: (_anchor: unknown, props: Record<string, any>) => {
        captured.flows.push(props);
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

import MetricCanvas from './MetricCanvas.svelte';

const metrics: MetricEntry[] = [
    { id: 'revenue', label: 'Revenue', expression: 'sum(amount) from fct__order', dataset_ref: 'fct__order' },
    { id: 'avg_price', label: 'Average price', binding: { dataset: 'fct__order', name: 'avg_price' } },
    { id: 'order_count', label: 'Order count', expression: 'count(*) from fct__order' },
];

const influences: MetricInfluence[] = [{ effect: 'revenue', drivers: ['avg_price', 'order_count'] }];

function lastFlow() {
    return captured.flows.at(-1) as Record<string, any>;
}

describe('MetricCanvas', () => {
    beforeEach(() => {
        captured.flows.length = 0;
    });

    afterEach(() => {
        cleanup();
    });

    it('renders one node per metric', () => {
        render(MetricCanvas, { props: { metrics, influences, layout: {} } });

        const nodes = lastFlow().nodes as Array<{ id: string; type: string }>;
        expect(nodes).toHaveLength(metrics.length);
        expect(nodes.map((node) => node.id)).toEqual(['revenue', 'avg_price', 'order_count']);
        expect(nodes.every((node) => node.type === 'metric')).toBe(true);
    });

    it('renders one edge per driver from effect (top) to driver (bottom), with no arrowhead or label', () => {
        render(MetricCanvas, { props: { metrics, influences, layout: {} } });

        const edges = lastFlow().edges as Array<Record<string, any>>;
        expect(edges).toHaveLength(2);
        expect(edges.map((edge) => [edge.source, edge.target])).toEqual([
            ['revenue', 'avg_price'],
            ['revenue', 'order_count'],
        ]);
        expect(edges.every((edge) => edge.type === 'influence')).toBe(true);
        expect(edges.every((edge) => edge.markerEnd === undefined)).toBe(true);
        expect(edges.every((edge) => edge.label === undefined)).toBe(true);
    });

    it('places nodes at the stored layout x position while locking y to the tree level and spacing drivers evenly around the effect', () => {
        render(MetricCanvas, {
            props: { metrics, influences, layout: { revenue: { x: 400, y: 250 } } },
        });

        const nodes = lastFlow().nodes as Array<{ id: string; position: { x: number; y: number } }>;
        expect(nodes.find((node) => node.id === 'revenue')?.position).toEqual({ x: 400, y: 80 });
        expect(nodes.find((node) => node.id === 'avg_price')?.position).toEqual({ x: 250, y: 270 });
        expect(nodes.find((node) => node.id === 'order_count')?.position).toEqual({ x: 550, y: 270 });
    });

    it('shows the empty state with a call to action instead of an empty canvas', async () => {
        const onaddmetric = vi.fn();
        const { container } = render(MetricCanvas, {
            props: { metrics: [], influences: [], layout: {}, onaddmetric },
        });

        expect(captured.flows).toHaveLength(0);
        expect(container.querySelector('[data-testid="metric-canvas-empty"]')).not.toBeNull();

        await fireEvent.click(container.querySelector('[data-testid="metric-canvas-empty-cta"]')!);
        expect(onaddmetric).toHaveBeenCalledOnce();
    });

    it('offers an add button above a populated canvas', async () => {
        const onaddmetric = vi.fn();
        const { container } = render(MetricCanvas, {
            props: { metrics, influences, layout: {}, onaddmetric },
        });

        await fireEvent.click(container.querySelector('[data-testid="metric-canvas-add"]')!);
        expect(onaddmetric).toHaveBeenCalledOnce();
    });

    it('reports a dragged connection with the upper source node as effect and lower target node as driver', () => {
        const onconnect = vi.fn();
        render(MetricCanvas, { props: { metrics, influences: [], layout: {}, onconnect } });

        lastFlow().onconnect({ source: 'revenue', target: 'order_count' });

        expect(onconnect).toHaveBeenCalledWith('order_count', 'revenue');
    });

    it('refuses a self-link before it ever reaches the page', () => {
        render(MetricCanvas, { props: { metrics, influences: [], layout: {} } });

        expect(lastFlow().isValidConnection({ source: 'revenue', target: 'revenue' })).toBe(false);
        expect(lastFlow().isValidConnection({ source: 'revenue', target: 'order_count' })).toBe(true);
    });

    it('refuses an influence that is already on the tree', () => {
        render(MetricCanvas, { props: { metrics, influences, layout: {} } });

        expect(lastFlow().isValidConnection({ source: 'revenue', target: 'avg_price' })).toBe(false);
    });

    it('reports a deleted edge as a driver and an effect', () => {
        const ondeleteedge = vi.fn();
        render(MetricCanvas, { props: { metrics, influences, layout: {}, ondeleteedge } });

        lastFlow().ondelete({ nodes: [], edges: [{ source: 'revenue', target: 'avg_price' }] });

        expect(ondeleteedge).toHaveBeenCalledWith('avg_price', 'revenue');
    });

    it('reports a deleted node as a metric id', () => {
        const ondeletemetric = vi.fn();
        render(MetricCanvas, { props: { metrics, influences, layout: {}, ondeletemetric } });

        lastFlow().ondelete({ nodes: [{ id: 'order_count' }], edges: [] });

        expect(ondeletemetric).toHaveBeenCalledWith('order_count');
    });

    it('reports where a node was dropped with x snapped to the grid and y locked to its tree level', () => {
        const onmove = vi.fn();
        render(MetricCanvas, { props: { metrics, influences, layout: {}, onmove } });

        lastFlow().onnodedragstop({
            targetNode: { id: 'revenue', position: { x: 123, y: 240 } },
            nodes: [],
            event: new MouseEvent('mouseup'),
        });

        expect(onmove).toHaveBeenCalledWith('revenue', { x: 120, y: 80 });
    });

    it('stays quiet on a drag end that has no target node', () => {
        const onmove = vi.fn();
        render(MetricCanvas, { props: { metrics, influences, layout: {}, onmove } });

        lastFlow().onnodedragstop({ targetNode: null, nodes: [], event: new MouseEvent('mouseup') });

        expect(onmove).not.toHaveBeenCalled();
    });

    it('reports node clicks and pane clicks so the page can drive the detail panel', () => {
        const onselectmetric = vi.fn();
        render(MetricCanvas, { props: { metrics, influences, layout: {}, onselectmetric } });

        lastFlow().onnodeclick({ node: { id: 'revenue' }, event: new MouseEvent('click') });
        expect(onselectmetric).toHaveBeenLastCalledWith('revenue');

        lastFlow().onpaneclick({ event: new MouseEvent('click') });
        expect(onselectmetric).toHaveBeenLastCalledWith(null);
    });
});
