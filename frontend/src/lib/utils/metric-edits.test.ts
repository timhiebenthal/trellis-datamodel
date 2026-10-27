import { describe, expect, it } from 'vitest';
import type { MetricCatalogEntry, MetricEntry, MetricInfluence } from '$lib/types';
import {
    addBoundMetric,
    addDraftMetric,
    connectInfluence,
    groupCatalog,
    metricLabelFromName,
    removeInfluence,
    removeMetric,
    type MetricGraphState,
} from './metric-edits';

function state(
    metrics: MetricEntry[] = [],
    influences: MetricInfluence[] = [],
): MetricGraphState {
    return { metrics, influences };
}

const revenue = { id: 'revenue', label: 'Revenue', expression: 'sum(amount)' };
const orders = { id: 'order_count', label: 'Order count', expression: 'count(*)' };

describe('addDraftMetric', () => {
    it('creates a draft with an id derived from the label and empty fields', () => {
        const { state: next, metric } = addDraftMetric(state(), 'Average price');

        expect(metric).toEqual({
            id: 'average_price',
            label: 'Average price',
            description: '',
            expression: '',
        });
        expect(next.metrics).toEqual([metric]);
        expect(next.influences).toEqual([]);
    });

    it('never reuses an id already on the canvas', () => {
        const existing = state([revenue]);
        const { state: next, metric } = addDraftMetric(existing, 'Revenue');

        expect(metric.id).toBe('revenue_1');
        expect(next.metrics.map((entry) => entry.id)).toEqual(['revenue', 'revenue_1']);
    });

    it('falls back to a readable label when the caller passes blank text', () => {
        const { metric } = addDraftMetric(state(), '   ');

        expect(metric.label).toBe('New metric');
        expect(metric.id).toBe('new_metric');
    });

    it('leaves the influences of the incoming state untouched', () => {
        const existing = state([revenue, orders], [{ effect: 'revenue', drivers: ['order_count'] }]);

        const { state: next } = addDraftMetric(existing, 'Cost');

        expect(next.influences).toEqual([{ effect: 'revenue', drivers: ['order_count'] }]);
        expect(existing.metrics).toHaveLength(2);
    });
});

describe('addBoundMetric', () => {
    const bindable: MetricCatalogEntry = {
        name: 'avg_price',
        dataset: 'fct__order',
        entity_id: 'order',
        bindable: true,
    };

    it('creates a reference: binding only, no expression and no description', () => {
        const { state: next, metric } = addBoundMetric(state(), bindable);

        expect(metric).toEqual({
            id: 'avg_price',
            label: 'Avg price',
            binding: { dataset: 'fct__order', name: 'avg_price' },
        });
        expect(metric?.expression).toBeUndefined();
        expect(metric?.description).toBeUndefined();
        expect(next.metrics).toHaveLength(1);
    });

    it('refuses an entry the backend marked read-only', () => {
        const readOnly: MetricCatalogEntry = {
            name: 'revenue',
            bindable: false,
            reason: 'Root-level metrics span datasets',
        };

        const result = addBoundMetric(state(), readOnly);

        expect(result.metric).toBeNull();
        expect(result.reason).toBe('not_bindable');
        expect(result.state.metrics).toEqual([]);
    });

    it('refuses the same binding twice', () => {
        const { state: first } = addBoundMetric(state(), bindable);

        const second = addBoundMetric(first, bindable);

        expect(second.metric).toBeNull();
        expect(second.reason).toBe('duplicate');
        expect(second.state.metrics).toHaveLength(1);
    });

    it('keeps the id unique against drafts already on the canvas', () => {
        const existing = state([{ id: 'avg_price', label: 'Avg price', expression: 'avg(amount)' }]);

        const { metric } = addBoundMetric(existing, bindable);

        expect(metric?.id).toBe('avg_price_1');
    });
});

describe('metricLabelFromName', () => {
    it('turns a semantic model name into a readable label', () => {
        expect(metricLabelFromName('avg_price')).toBe('Avg price');
        expect(metricLabelFromName('order_count')).toBe('Order count');
        expect(metricLabelFromName('aov')).toBe('Aov');
        expect(metricLabelFromName('Average price')).toBe('Average price');
    });
});

describe('connectInfluence', () => {
    const canvas = state([revenue, orders]);

    it('creates an influence with the drag source as driver and the target as effect', () => {
        const result = connectInfluence(canvas, 'order_count', 'revenue');

        expect(result.ok).toBe(true);
        expect(result.state.influences).toEqual([{ effect: 'revenue', drivers: ['order_count'] }]);
    });

    it('appends a second known driver to the same effect', () => {
        const withPrice = { ...canvas, metrics: [...canvas.metrics, { id: 'avg_price', label: 'Avg price' }] };
        const first = connectInfluence(withPrice, 'order_count', 'revenue');
        const second = connectInfluence(first.state, 'avg_price', 'revenue');

        expect(second.ok).toBe(true);
        expect(second.state.influences).toEqual([
            { effect: 'revenue', drivers: ['order_count', 'avg_price'] },
        ]);
    });

    it('refuses a self-link', () => {
        const result = connectInfluence(canvas, 'revenue', 'revenue');

        expect(result.ok).toBe(false);
        expect(result.reason).toBe('self');
        expect(result.state.influences).toEqual([]);
    });

    it('refuses a duplicate and leaves the graph alone', () => {
        const first = connectInfluence(canvas, 'order_count', 'revenue');
        const again = connectInfluence(first.state, 'order_count', 'revenue');

        expect(again.ok).toBe(false);
        expect(again.reason).toBe('duplicate');
        expect(again.state.influences).toEqual([{ effect: 'revenue', drivers: ['order_count'] }]);
    });

    it('refuses an influence that references a metric not on the canvas', () => {
        const result = connectInfluence(canvas, 'ghost', 'revenue');

        expect(result.ok).toBe(false);
        expect(result.reason).toBe('unknown');
        expect(result.state.influences).toEqual([]);
    });

    it('does not mutate the state it was given', () => {
        const before = JSON.stringify(canvas);
        connectInfluence(canvas, 'order_count', 'revenue');

        expect(JSON.stringify(canvas)).toBe(before);
    });
});

describe('removeInfluence', () => {
    it('removes only the named driver from the effect entry', () => {
        const graph = state(
            [{ id: 'revenue', label: 'Revenue' }, { id: 'a', label: 'A' }, { id: 'b', label: 'B' }],
            [{ effect: 'revenue', drivers: ['a', 'b'] }],
        );

        const next = removeInfluence(graph, 'a', 'revenue');

        expect(next.influences).toEqual([{ effect: 'revenue', drivers: ['b'] }]);
    });

    it('deletes the entry when its last driver goes', () => {
        const graph = state(
            [{ id: 'revenue', label: 'Revenue' }, { id: 'a', label: 'A' }],
            [{ effect: 'revenue', drivers: ['a'] }],
        );

        const next = removeInfluence(graph, 'a', 'revenue');

        expect(next.influences).toEqual([]);
        expect(next.metrics).toHaveLength(2);
    });

    it('is a no-op when the edge is not there', () => {
        const graph = state([{ id: 'revenue', label: 'Revenue' }], []);

        expect(removeInfluence(graph, 'a', 'revenue').influences).toEqual([]);
    });
});

describe('removeMetric', () => {
    const graph = state(
        [
            { id: 'revenue', label: 'Revenue' },
            { id: 'order_count', label: 'Order count' },
            { id: 'avg_price', label: 'Avg price' },
        ],
        [
            { effect: 'revenue', drivers: ['order_count', 'avg_price'] },
            { effect: 'avg_price', drivers: ['order_count'] },
        ],
    );

    it('drops the metric from the canvas', () => {
        const next = removeMetric(graph, 'avg_price');

        expect(next.metrics.map((metric) => metric.id)).toEqual(['revenue', 'order_count']);
    });

    it('drops the metric from every drivers list', () => {
        const next = removeMetric(graph, 'avg_price');

        expect(next.influences).toEqual([{ effect: 'revenue', drivers: ['order_count'] }]);
    });

    it('drops influence entries whose driver list empties', () => {
        const next = removeMetric(graph, 'order_count');

        expect(next.influences).toEqual([{ effect: 'revenue', drivers: ['avg_price'] }]);
    });

    it('drops influence entries for which the removed metric was the effect', () => {
        const next = removeMetric(graph, 'revenue');

        expect(next.influences).toEqual([{ effect: 'avg_price', drivers: ['order_count'] }]);
        expect(next.metrics).toHaveLength(2);
    });

    it('is a no-op for an unknown id', () => {
        const next = removeMetric(graph, 'ghost');

        expect(next.metrics).toHaveLength(3);
        expect(next.influences).toHaveLength(2);
    });
});

describe('groupCatalog', () => {
    const catalog: MetricCatalogEntry[] = [
        { name: 'avg_price', dataset: 'fct__order', entity_id: 'order', bindable: true },
        { name: 'revenue', bindable: false, reason: 'Cross-dataset metric' },
        { name: 'order_count', dataset: 'fct__order', entity_id: 'order', bindable: true },
    ];

    it('splits the catalog into addable, already added, and read-only', () => {
        const metrics: MetricEntry[] = [
            { id: 'avg_price', label: 'Avg price', binding: { dataset: 'fct__order', name: 'avg_price' } },
        ];

        const groups = groupCatalog(catalog, metrics);

        expect(groups.added.map((entry) => entry.name)).toEqual(['avg_price']);
        expect(groups.available.map((entry) => entry.name)).toEqual(['order_count']);
        expect(groups.unavailable.map((entry) => entry.name)).toEqual(['revenue']);
        expect(groups.unavailable[0].reason).toBe('Cross-dataset metric');
    });

    it('treats every bindable entry as available on an empty canvas', () => {
        const groups = groupCatalog(catalog, []);

        expect(groups.available.map((entry) => entry.name)).toEqual(['avg_price', 'order_count']);
        expect(groups.added).toEqual([]);
    });

    it('does not mistake a draft for a bound entry', () => {
        const groups = groupCatalog(catalog, [{ id: 'avg_price', label: 'Avg price', expression: 'avg(x)' }]);

        expect(groups.added).toEqual([]);
        expect(groups.available.map((entry) => entry.name)).toEqual(['avg_price', 'order_count']);
    });
});
