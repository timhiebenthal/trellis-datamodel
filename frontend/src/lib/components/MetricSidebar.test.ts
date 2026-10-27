import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
import type { MetricCatalogEntry, MetricEntry } from '$lib/types';
import MetricSidebar from './MetricSidebar.svelte';

const metrics: MetricEntry[] = [
    { id: 'revenue', label: 'Revenue', expression: 'sum(amount)', dataset_ref: 'fct__order' },
    { id: 'avg_price', label: 'Avg price', binding: { dataset: 'fct__order', name: 'avg_price' } },
];

const catalog: MetricCatalogEntry[] = [
    { name: 'order_count', dataset: 'fct__order', entity_id: 'order', bindable: true },
    { name: 'avg_price', dataset: 'fct__order', entity_id: 'order', bindable: true },
    { name: 'revenue', bindable: false, reason: 'Cross-dataset metric - no single entity to bind to' },
];

describe('MetricSidebar', () => {
    afterEach(() => {
        cleanup();
    });

    it('lists the metrics already on the tree with their dataset or binding', () => {
        const { container } = render(MetricSidebar, { props: { metrics, catalog: [] } });

        const rows = Array.from(container.querySelectorAll('[data-testid="metric-sidebar-entry"]'));
        expect(rows).toHaveLength(2);
        expect(rows[0].textContent).toContain('Revenue');
        expect(rows[0].textContent).toContain('fct__order');
        expect(rows[1].textContent).toContain('Avg price');
        expect(rows[1].textContent).toContain('bound · fct__order');
    });

    it('creates a draft from the add action', async () => {
        const onaddmetric = vi.fn();
        const { container } = render(MetricSidebar, { props: { metrics: [], catalog: [], onaddmetric } });

        await fireEvent.click(container.querySelector('[data-testid="metric-sidebar-add"]')!);

        expect(onaddmetric).toHaveBeenCalledOnce();
    });

    it('offers only the not-yet-added bindable catalog entries as addable', () => {
        const { container } = render(MetricSidebar, { props: { metrics, catalog } });

        const addable = Array.from(
            container.querySelectorAll('[data-testid="metric-sidebar-catalog-add"]'),
        );
        expect(addable).toHaveLength(1);
        expect(addable[0].textContent).toContain('order_count');
    });

    it('adds a bindable catalog entry through the callback', async () => {
        const onaddcatalogmetric = vi.fn();
        const { container } = render(MetricSidebar, {
            props: { metrics, catalog, onaddcatalogmetric },
        });

        await fireEvent.click(container.querySelector('[data-testid="metric-sidebar-catalog-add"]')!);

        expect(onaddcatalogmetric).toHaveBeenCalledWith(catalog[0]);
    });

    it('marks an already bound entry as added instead of offering it again', () => {
        const { container } = render(MetricSidebar, { props: { metrics, catalog } });

        const added = Array.from(
            container.querySelectorAll('[data-testid="metric-sidebar-catalog-added"]'),
        );
        expect(added).toHaveLength(1);
        expect(added[0].textContent).toContain('avg_price');
    });

    it('greys out a read-only entry and shows the reason as a tooltip', () => {
        const { container } = render(MetricSidebar, { props: { metrics, catalog } });

        const readOnly = container.querySelector('[data-testid="metric-sidebar-catalog-readonly"]');
        expect(readOnly?.textContent).toContain('revenue');
        expect(readOnly?.getAttribute('title')).toBe(catalog[2].reason);
        expect(readOnly?.getAttribute('data-readonly')).toBe('true');
        expect(readOnly?.querySelector('button')).toBeNull();
    });

    it('selects and deletes tree entries through the callbacks', async () => {
        const onselectmetric = vi.fn();
        const ondeletemetric = vi.fn();
        const { container } = render(MetricSidebar, {
            props: { metrics, catalog, onselectmetric, ondeletemetric },
        });

        await fireEvent.click(container.querySelector('[data-testid="metric-sidebar-select"]')!);
        expect(onselectmetric).toHaveBeenCalledWith('revenue');

        await fireEvent.click(container.querySelector('[data-testid="metric-sidebar-delete"]')!);
        expect(ondeletemetric).toHaveBeenCalledWith('revenue');
    });

    it('explains an empty catalog instead of showing an empty section', () => {
        const { container } = render(MetricSidebar, { props: { metrics: [], catalog: [] } });

        expect(container.textContent).toContain('No metrics found in the semantic model yet.');
        expect(container.textContent).toContain('Nothing yet.');
    });
});
