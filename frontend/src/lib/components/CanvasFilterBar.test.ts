import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { domainFilter, frameworkModels, nodes, tagFilter } from '$lib/stores';
import CanvasFilterBar from './CanvasFilterBar.svelte';

describe('CanvasFilterBar', () => {
    beforeEach(() => {
        domainFilter.set([]);
        tagFilter.set([]);
        frameworkModels.set([
            {
                unique_id: 'model.project.orders',
                name: 'orders',
                schema: 'public',
                table: 'orders',
                columns: [],
                tags: ['model-tag'],
            },
        ]);
        nodes.set([
            {
                id: 'orders',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Orders',
                    model_ref: 'model.project.orders',
                    domain: 'Sales',
                    domains: ['Sales', 'Commerce'],
                    tags: ['entity-tag'],
                    framework_tags: ['bound-tag'],
                    ui_tags: ['ui-tag'],
                },
            },
            {
                id: 'customers',
                type: 'entity',
                position: { x: 100, y: 0 },
                data: {
                    label: 'Customers',
                    domains: ['Marketing'],
                    tags: ['customer-tag'],
                },
            },
        ] as any);
    });

    afterEach(() => {
        cleanup();
    });

    it('renders active domain and tag chips with filtered state and visible count', () => {
        domainFilter.set(['Sales']);
        tagFilter.set(['model-tag', 'ui-tag']);

        render(CanvasFilterBar, { props: { visibleCount: 1, totalCount: 2 } });

        expect(document.querySelector('[role="status"]')?.textContent).toContain('Filtered');
        expect(document.querySelector('[data-testid="canvas-filter-domain-chip"]')?.textContent).toContain('Sales');
        expect(
            Array.from(document.querySelectorAll('[data-testid="canvas-filter-tag-chip"]')).map(
                (chip) => chip.textContent,
            ),
        ).toEqual(expect.arrayContaining([expect.stringContaining('model-tag'), expect.stringContaining('ui-tag')]));
        expect(document.body.textContent).toContain('Showing 1 of 2 entities');
    });

    it('clears domain and tag filters with one accessible action', async () => {
        domainFilter.set(['Sales']);
        tagFilter.set(['ui-tag']);

        render(CanvasFilterBar, { props: { visibleCount: 1, totalCount: 2 } });

        await fireEvent.click(document.querySelector('button[aria-label="Clear Canvas filters"]')!);

        expect(get(domainFilter)).toEqual([]);
        expect(get(tagFilter)).toEqual([]);
    });

    it('selects a domain from singular and list domain metadata', async () => {
        render(CanvasFilterBar, { props: { visibleCount: 2, totalCount: 2 } });

        const select = document.querySelector('select[aria-label="Add Canvas domain filter"]') as HTMLSelectElement;
        expect(Array.from(select.options).map((option) => option.value)).toEqual([
            '',
            'Commerce',
            'Marketing',
            'Sales',
        ]);

        await fireEvent.change(select, { target: { value: 'Commerce' } });

        expect(get(domainFilter)).toEqual(['Commerce']);
    });

    it('offers normalized tags from model, framework, UI, and entity metadata', () => {
        render(CanvasFilterBar, { props: { visibleCount: 2, totalCount: 2 } });

        const select = document.querySelector('select[aria-label="Add Canvas tag filter"]') as HTMLSelectElement;
        expect(Array.from(select.options).map((option) => option.value)).toEqual([
            '',
            'bound-tag',
            'customer-tag',
            'entity-tag',
            'model-tag',
            'ui-tag',
        ]);
    });
});
