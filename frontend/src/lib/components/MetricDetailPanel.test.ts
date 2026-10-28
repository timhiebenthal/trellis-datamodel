import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
import type { MetricEntry } from '$lib/types';
import MetricDetailPanel from './MetricDetailPanel.svelte';

const draft: MetricEntry = {
    id: 'revenue',
    label: 'Revenue',
    description: 'Booked revenue for the period.',
    expression: 'sum(amount) from fct__order',
    dataset_ref: 'fct__order',
};

const bound: MetricEntry = {
    id: 'avg_price',
    label: 'Avg price',
    binding: { dataset: 'fct__order', name: 'avg_price' },
};

function field(
    container: HTMLElement,
    name: string,
): HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement {
    return container.querySelector(`[data-testid="metric-field-${name}"]`) as
        | HTMLInputElement
        | HTMLTextAreaElement
        | HTMLSelectElement;
}

describe('MetricDetailPanel', () => {
    afterEach(() => {
        cleanup();
    });

    it('invites a selection when nothing is selected', () => {
        const { container } = render(MetricDetailPanel, { props: { metric: null } });

        expect(container.textContent).toContain('Select a metric');
        expect(container.querySelector('[data-testid="metric-field-label"]')).toBeNull();
    });

    it('prefills a draft metric and reports edits', async () => {
        const onchange = vi.fn();
        const { container } = render(MetricDetailPanel, { props: { metric: draft, onchange } });

        expect(field(container, 'label').value).toBe('Revenue');
        expect(field(container, 'description').value).toBe('Booked revenue for the period.');
        expect(field(container, 'expression').value).toBe('sum(amount) from fct__order');
        expect(field(container, 'dataset').value).toBe('fct__order');

        await fireEvent.input(field(container, 'label'), { target: { value: 'Booked revenue' } });
        await fireEvent.input(field(container, 'expression'), { target: { value: 'sum(net_amount)' } });

        expect(onchange).toHaveBeenCalledWith({ label: 'Booked revenue' });
        expect(onchange).toHaveBeenCalledWith({ expression: 'sum(net_amount)' });
    });

    it('offers only the exported datasets and reports the one picked', async () => {
        const onchange = vi.fn();
        const { container } = render(MetricDetailPanel, {
            props: { metric: draft, datasets: ['fct__order', 'dim_customer'], onchange },
        });

        const select = field(container, 'dataset') as HTMLSelectElement;
        expect(select.tagName).toBe('SELECT');
        expect(select.value).toBe('fct__order');
        expect(Array.from(select.options).map((option) => option.textContent?.trim())).toEqual([
            'None - document level',
            'fct__order',
            'dim_customer',
        ]);

        await fireEvent.change(select, { target: { value: 'dim_customer' } });
        expect(onchange).toHaveBeenCalledWith({ dataset_ref: 'dim_customer' });

        await fireEvent.change(select, { target: { value: '' } });
        expect(onchange).toHaveBeenLastCalledWith({ dataset_ref: undefined });
    });

    it('keeps a dataset that is no longer exported visible instead of blanking it', () => {
        const { container } = render(MetricDetailPanel, {
            props: { metric: { ...draft, dataset_ref: 'ghost' }, datasets: ['fct__order'] },
        });

        const select = field(container, 'dataset') as HTMLSelectElement;
        expect(select.value).toBe('ghost');
        expect(Array.from(select.options).map((option) => option.textContent?.trim())).toContain(
            'ghost (not exported)',
        );
    });

    it('disables the dataset picker and says why when nothing is exported', () => {
        const { container } = render(MetricDetailPanel, {
            props: { metric: { ...draft, dataset_ref: undefined }, datasets: [] },
        });

        expect((field(container, 'dataset') as HTMLSelectElement).disabled).toBe(true);
        expect(container.textContent).toContain('No dataset is exported yet');
    });

    it('marks a draft with no expression as required', () => {
        const { container } = render(MetricDetailPanel, {
            props: { metric: { id: 'new_metric', label: 'New metric', description: '', expression: '' } },
        });

        expect(container.textContent).toContain('Expression required');
    });

    it('shows a bound metric as a read-only reference with an unlink action', async () => {
        const onunlink = vi.fn();
        const { container } = render(MetricDetailPanel, { props: { metric: bound, onunlink } });

        expect(container.textContent).toContain('fct__order.avg_price');
        expect(field(container, 'expression')).toBeNull();
        expect(field(container, 'label')).toBeNull();

        await fireEvent.click(container.querySelector('[data-testid="metric-unlink"]')!);
        expect(onunlink).toHaveBeenCalledWith('avg_price');
    });

    it('shows the resolved expression of a bound metric without letting it be edited', () => {
        const { container } = render(MetricDetailPanel, {
            props: { metric: { ...bound, resolved_expression: 'avg(amount)' } },
        });

        const expression = container.querySelector('[data-testid="metric-resolved-expression"]');
        expect(expression?.textContent).toBe('avg(amount)');
        expect(field(container, 'expression')).toBeNull();
        expect(container.querySelector('[data-testid="metric-resolved-expression"] textarea')).toBeNull();
    });

    it('explains where a bound definition lives when the expression is absent', () => {
        const { container } = render(MetricDetailPanel, { props: { metric: bound } });

        expect(container.querySelector('[data-testid="metric-resolved-expression"]')).toBeNull();
        expect(container.textContent).toContain('never a copy');
    });

    it('lists every server warning on its own line', () => {
        const { container } = render(MetricDetailPanel, {
            props: {
                metric: draft,
                warnings: ['revenue: dataset_ref fct__order no longer resolves', 'orders: binding gone'],
            },
        });

        const lines = Array.from(container.querySelectorAll('[data-testid="metric-warning"]'));
        expect(lines).toHaveLength(2);
        expect(lines[0].textContent).toContain('no longer resolves');
    });

    it('shows a failed save without hiding the edit', () => {
        const { container } = render(MetricDetailPanel, {
            props: { metric: draft, error: 'Failed to save metric tree: 422' },
        });

        expect(container.querySelector('[role="alert"]')?.textContent).toContain('422');
        expect(field(container, 'expression').value).toBe('sum(amount) from fct__order');
    });

    it('reports save status', () => {
        const saving = render(MetricDetailPanel, { props: { metric: draft, isSaving: true } });
        expect(saving.container.textContent).toContain('Saving');

        cleanup();

        const unsaved = render(MetricDetailPanel, {
            props: { metric: draft, hasUnsavedChanges: true },
        });
        expect(unsaved.container.textContent).toContain('Unsaved changes');

        cleanup();

        const saved = render(MetricDetailPanel, { props: { metric: draft } });
        expect(saved.container.textContent).toContain('All changes saved');
    });

    it('says autosave is paused while any draft is incomplete', () => {
        const { container } = render(MetricDetailPanel, {
            props: { metric: draft, incompleteIds: ['revenue', 'new_metric'] },
        });

        expect(container.textContent).toContain('Auto-save paused');
        expect(container.textContent).toContain('2');
    });

    it('focuses the label field when asked, so a new metric can be named immediately', () => {
        const { container } = render(MetricDetailPanel, { props: { metric: draft, focus: 'label' } });

        expect(document.activeElement).toBe(field(container, 'label'));
    });

    it('closes from the header', async () => {
        const onclose = vi.fn();
        const { container } = render(MetricDetailPanel, { props: { metric: draft, onclose } });

        await fireEvent.click(container.querySelector('[data-testid="metric-detail-close"]')!);
        expect(onclose).toHaveBeenCalledOnce();
    });
});
