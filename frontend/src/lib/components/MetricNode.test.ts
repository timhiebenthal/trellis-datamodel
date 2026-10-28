import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
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

    it('removes the metric through the action the canvas publishes', async () => {
        const deleteMetric = vi.fn();
        const { container } = render(MetricNode, {
            props: {
                id: 'revenue',
                type: 'metric',
                data: { metric: { id: 'revenue', label: 'Revenue' }, unresolved: false },
                selected: false,
            } as any,
            context: new Map<string, unknown>([['metricCanvas', { deleteMetric }]]),
        });

        await fireEvent.click(container.querySelector('[data-testid="metric-node-delete"]')!);

        expect(deleteMetric).toHaveBeenCalledWith('revenue');
    });

    it('hides the remove action when nothing is listening', () => {
        const { container } = renderNode({ id: 'revenue', label: 'Revenue' });

        expect(container.querySelector('[data-testid="metric-node-delete"]')).toBeNull();
    });

    it('opens the + Add driver / + Add effect popover and triggers related metric actions', async () => {
        const addRelatedDraft = vi.fn();
        const addRelatedCatalogMetric = vi.fn();
        const connectRelatedMetric = vi.fn();
        const catalogEntry = {
            name: 'project_end_date',
            dataset: 'entity_booking',
            entity_id: 'entity_booking',
            bindable: true,
        };

        const { container } = render(MetricNode, {
            props: {
                id: 'revenue',
                type: 'metric',
                data: { metric: { id: 'revenue', label: 'Revenue' }, unresolved: false },
                selected: false,
            } as any,
            context: new Map<string, unknown>([
                [
                    'metricCanvas',
                    {
                        getMetrics: () => [
                            { id: 'revenue', label: 'Revenue' },
                            { id: 'orders', label: 'Orders' },
                        ],
                        getCatalog: () => [catalogEntry],
                        getInfluences: () => [],
                        addRelatedDraft,
                        addRelatedCatalogMetric,
                        connectRelatedMetric,
                    },
                ],
            ]),
        });

        const addDriverBtn = container.querySelector('[data-testid="metric-node-add-driver"]')!;
        expect(addDriverBtn.textContent).toContain('Add driver');

        await fireEvent.click(addDriverBtn);

        const picker = container.querySelector('[data-testid="metric-node-picker"]');
        expect(picker).not.toBeNull();
        expect(picker?.getAttribute('data-relation')).toBe('driver');

        // Pick a semantic model metric from the popover
        const catalogBtn = container.querySelector(
            '[data-testid="metric-node-picker-catalog-item"]',
        )!;
        expect(catalogBtn.textContent).toContain('project_end_date');
        await fireEvent.click(catalogBtn);

        expect(addRelatedCatalogMetric).toHaveBeenCalledWith('revenue', 'driver', catalogEntry);
        expect(container.querySelector('[data-testid="metric-node-picker"]')).toBeNull();

        // Open + Add effect popover and create a new draft effect
        await fireEvent.click(container.querySelector('[data-testid="metric-node-add-effect"]')!);
        await fireEvent.click(container.querySelector('[data-testid="metric-node-picker-draft"]')!);
        expect(addRelatedDraft).toHaveBeenCalledWith('revenue', 'effect');
    });
});
