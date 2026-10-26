import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import type { MetricEntry } from '$lib/types';

vi.mock('@xyflow/svelte', () => ({
    Handle: () => {},
    Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
    useSvelteFlow: () => ({ updateNodeData: vi.fn(), getNode: vi.fn() }),
}));

import MetricNode from './MetricNode.svelte';

function renderNode(metric: MetricEntry, unresolved = false) {
    return render(MetricNode, {
        props: {
            id: metric.id,
            type: 'metric',
            data: { metric, unresolved },
            selected: false,
        } as any,
    });
}

describe('MetricNode', () => {
    afterEach(() => {
        cleanup();
    });

    it('always shows the label', () => {
        const { container } = renderNode({ id: 'revenue', label: 'Revenue' });

        expect(container.textContent).toContain('Revenue');
    });

    it('shows a dataset badge for a draft with a dataset_ref', () => {
        const { container } = renderNode({
            id: 'revenue',
            label: 'Revenue',
            expression: 'sum(amount)',
            dataset_ref: 'fct__order',
        });

        expect(container.querySelector('[data-testid="metric-node-dataset"]')?.textContent).toContain('fct__order');
        expect(container.querySelector('[data-testid="metric-node-bound"]')).toBeNull();
        expect(container.querySelector('[data-testid="metric-node-unbound"]')).toBeNull();
        expect(container.textContent).toContain('sum(amount)');
    });

    it('shows "unbound" when the metric has no dataset at all', () => {
        const { container } = renderNode({ id: 'revenue', label: 'Revenue', expression: 'sum(amount)' });

        expect(container.querySelector('[data-testid="metric-node-unbound"]')?.textContent).toContain('unbound');
        expect(container.querySelector('[data-testid="metric-node-dataset"]')).toBeNull();
    });

    it('marks a bound metric with its dataset name', () => {
        const { container } = renderNode({
            id: 'avg_price',
            label: 'Average price',
            binding: { dataset: 'fct__order', name: 'avg_price' },
        });

        const bound = container.querySelector('[data-testid="metric-node-bound"]');
        expect(bound?.textContent).toContain('bound');
        expect(bound?.textContent).toContain('fct__order');
        // A bound entry is a reference, so there is no expression to show.
        expect(container.querySelector('p.font-mono')).toBeNull();
    });

    it('badges an unresolved metric and explains why on hover', () => {
        const { container } = renderNode(
            {
                id: 'avg_price',
                label: 'Average price',
                binding: { dataset: 'fct__order', name: 'avg_price' },
            },
            true,
        );

        const badge = container.querySelector('[data-testid="metric-node-unresolved"]');
        expect(badge?.textContent).toContain('unresolved');
        expect(badge?.getAttribute('title')).toContain('fct__order.avg_price');
    });

    it('does not badge a metric that resolves', () => {
        const { container } = renderNode({ id: 'revenue', label: 'Revenue', expression: 'sum(amount)' });

        expect(container.querySelector('[data-testid="metric-node-unresolved"]')).toBeNull();
    });
});
