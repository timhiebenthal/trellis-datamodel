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

    it('lists a draft and a bound metric under one dataset, ahead of what is still to add', () => {
        const { container } = render(MetricSidebar, { props: { metrics, catalog } });

        const group = container.querySelector('[data-group-key="fct__order"]')!;

        const rows = Array.from(group.querySelectorAll('[data-testid="metric-sidebar-entry"]'));
        expect(rows).toHaveLength(2);
        expect(rows[0].textContent).toContain('Revenue');
        expect(rows[0].textContent).toContain('draft');
        expect(rows[1].textContent).toContain('avg_price');
        expect(rows[1].textContent).not.toContain('draft');
        expect(group.querySelectorAll('[data-testid="metric-sidebar-catalog-add"]')).toHaveLength(1);
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

    it('explains an empty sidebar instead of showing nothing', () => {
        const { container } = render(MetricSidebar, { props: { metrics: [], catalog: [] } });

        expect(container.textContent).toContain('No metrics yet.');
        expect(container.querySelector('[data-testid="metric-sidebar-dataset-group"]')).toBeNull();
    });

    it('says so when the search matches nothing', async () => {
        const { container } = render(MetricSidebar, { props: { metrics, catalog } });

        await fireEvent.input(
            container.querySelector('[data-testid="metric-sidebar-search"]') as HTMLInputElement,
            { target: { value: 'no-such-metric' } },
        );

        expect(container.textContent).toContain('No matching metrics.');
    });

    it('filters both tree metrics and semantic model catalog entries via the search bar', async () => {
        const { container } = render(MetricSidebar, { props: { metrics, catalog } });
        const searchInput = container.querySelector(
            '[data-testid="metric-sidebar-search"]',
        ) as HTMLInputElement;
        expect(searchInput).not.toBeNull();

        await fireEvent.input(searchInput, { target: { value: 'order_count' } });

        const treeRows = Array.from(
            container.querySelectorAll('[data-testid="metric-sidebar-entry"]'),
        );
        expect(treeRows).toHaveLength(0);

        const addable = Array.from(
            container.querySelectorAll('[data-testid="metric-sidebar-catalog-add"]'),
        );
        expect(addable).toHaveLength(1);
        expect(addable[0].textContent).toContain('order_count');

        await fireEvent.input(searchInput, { target: { value: 'revenue' } });
        expect(container.querySelectorAll('[data-testid="metric-sidebar-entry"]')).toHaveLength(1);
        expect(
            container.querySelectorAll('[data-testid="metric-sidebar-catalog-readonly"]'),
        ).toHaveLength(1);
        expect(
            container.querySelectorAll('[data-testid="metric-sidebar-catalog-add"]'),
        ).toHaveLength(0);
    });

    it('groups metrics by dataset and toggles collapse on click', async () => {
        const multiDatasetCatalog: MetricCatalogEntry[] = [
            { name: 'order_count', dataset: 'fct__order', entity_id: 'order', bindable: true },
            { name: 'avg_price', dataset: 'fct__order', entity_id: 'order', bindable: true },
            { name: 'booking_hours', dataset: 'entity_booking', entity_id: 'entity_booking', bindable: true },
            { name: 'revenue', bindable: false, reason: 'Cross-dataset metric' },
        ];
        const { container } = render(MetricSidebar, {
            props: { metrics, catalog: multiDatasetCatalog },
        });

        const groups = Array.from(
            container.querySelectorAll('[data-testid="metric-sidebar-dataset-group"]'),
        );
        expect(groups.map((g) => g.getAttribute('data-group-key'))).toEqual([
            'entity_booking',
            'fct__order',
            '__cross_dataset__',
        ]);

        // Collapse entity_booking
        const firstToggle = groups[0].querySelector(
            '[data-testid="metric-sidebar-dataset-group-toggle"]',
        )!;
        await fireEvent.click(firstToggle);
        expect(groups[0].querySelectorAll('[data-testid="metric-sidebar-catalog-add"]')).toHaveLength(0);

        // Expand entity_booking again
        await fireEvent.click(firstToggle);
        expect(groups[0].querySelectorAll('[data-testid="metric-sidebar-catalog-add"]')).toHaveLength(1);
    });

    it('highlights an added catalog entry in teal and selects the bound metric on click', async () => {
        const onselectmetric = vi.fn();
        const { container } = render(MetricSidebar, {
            props: { metrics, catalog, selectedMetricId: 'avg_price', onselectmetric },
        });

        const added = container.querySelector('[data-testid="metric-sidebar-catalog-added"]') as HTMLElement;
        expect(added).not.toBeNull();
        expect(added.className).toContain('bg-primary-100');

        await fireEvent.click(added.querySelector('[data-testid="metric-sidebar-select"]')!);
        expect(onselectmetric).toHaveBeenCalledWith('avg_price');
    });
});
