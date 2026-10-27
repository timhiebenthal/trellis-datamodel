import { describe, expect, it } from 'vitest';
import type { MetricCatalogEntry, MetricEntry, MetricInfluence } from '$lib/types';
import {
    addBoundMetric,
    addDraftMetric,
    connectInfluence,
    groupCatalog,
    groupCatalogByDataset,
    incompleteDraftIds,
    metricLabelFromName,
    removeInfluence,
    removeMetric,
    unlinkMetric,
    updateMetric,
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

describe('groupCatalog', () => {    const catalog: MetricCatalogEntry[] = [
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

describe('groupCatalogByDataset', () => {
    const catalog: MetricCatalogEntry[] = [
        { name: 'avg_rate', dataset: 'entity_booking', entity_id: 'booking', bindable: true },
        { name: 'hours', dataset: 'entity_booking', entity_id: 'booking', bindable: true },
        { name: 'order_count', dataset: 'fct__order', entity_id: 'order', bindable: true },
        { name: 'orphan_metric', dataset: 'unmapped_dataset', entity_id: null, bindable: false, reason: 'no entity' },
        { name: 'revenue', bindable: false, reason: 'Cross-dataset metric' },
    ];
    const bound: MetricEntry = {
        id: 'avg_rate',
        label: 'Avg rate',
        binding: { dataset: 'entity_booking', name: 'avg_rate' },
    };
    const draft: MetricEntry = {
        id: 'margin',
        label: 'Margin',
        expression: 'a - b',
        dataset_ref: 'entity_booking',
    };

    const shape = (group: { items: Array<{ kind: string; status: string }> }) =>
        group.items.map((item) => `${item.kind}:${item.status}`);

    it('keeps a draft, a bound metric and an addable one together under their dataset', () => {
        const groups = groupCatalogByDataset(catalog, [draft, bound]);
        const booking = groups.find((group) => group.key === 'entity_booking');

        expect(booking?.label).toBe('entity_booking');
        expect(booking?.onTreeCount).toBe(2);
        expect(shape(booking!)).toEqual(['tree:draft', 'tree:added', 'catalog:available']);
    });

    it('orders datasets by name, then drafts without a dataset, then cross-dataset metrics', () => {
        const groups = groupCatalogByDataset(catalog, [
            { id: 'loose', label: 'Loose', expression: 'x' },
        ]);

        expect(groups.map((group) => group.label)).toEqual([
            'entity_booking',
            'fct__order',
            'unmapped_dataset',
            'No dataset',
            'Cross-dataset',
        ]);
        expect(groups.map((group) => group.kind)).toEqual([
            'dataset',
            'dataset',
            'dataset',
            'no-dataset',
            'cross-dataset',
        ]);
    });

    it('groups a binding the catalog no longer lists under its dataset name', () => {
        const stale: MetricEntry = {
            id: 'gone',
            label: 'Gone',
            binding: { dataset: 'old_dataset', name: 'gone' },
        };

        const groups = groupCatalogByDataset(catalog, [stale]);

        expect(groups.find((group) => group.key === 'old_dataset')?.items).toHaveLength(1);
    });

    it('still shows a bound metric when a filter hides its catalog entries', () => {
        const groups = groupCatalogByDataset(catalog, [bound], {
            catalog: () => false,
            metric: () => true,
        });

        expect(groups.map((group) => group.key)).toEqual(['entity_booking']);
        expect(shape(groups[0])).toEqual(['tree:added']);
    });

    it('shows the bound metric when only its catalog entry matches the filter', () => {
        const groups = groupCatalogByDataset(catalog, [bound], {
            catalog: (entry) => entry.name === 'avg_rate',
            metric: () => false,
        });

        expect(groups.map((group) => group.key)).toEqual(['entity_booking']);
        expect(shape(groups[0])).toEqual(['tree:added']);
    });
});

describe('updateMetric', () => {
    const graph = state([
        { id: 'revenue', label: 'Revenue', description: '', expression: 'sum(amount)' },
        { id: 'avg_price', label: 'Avg price', binding: { dataset: 'fct__order', name: 'avg_price' } },
    ]);

    it('edits the draft fields without touching the id', () => {
        const next = updateMetric(graph, 'revenue', {
            label: 'Booked revenue',
            description: 'Booked revenue for the period.',
            expression: 'sum(amount) from fct__order',
            dataset_ref: 'fct__order',
        });

        expect(next.metrics[0]).toEqual({
            id: 'revenue',
            label: 'Booked revenue',
            description: 'Booked revenue for the period.',
            expression: 'sum(amount) from fct__order',
            dataset_ref: 'fct__order',
        });
    });

    it('ignores an attempted id change so influences keep pointing at the metric', () => {
        const next = updateMetric(graph, 'revenue', { id: 'revenue_v2', label: 'Renamed' } as Partial<MetricEntry>);

        expect(next.metrics[0].id).toBe('revenue');
        expect(next.metrics[0].label).toBe('Renamed');
    });

    it('never lets a bound entry pick up an expression or description', () => {
        const next = updateMetric(graph, 'avg_price', {
            expression: 'avg(amount)',
            description: 'copied definition',
        });

        expect(next.metrics[1].expression).toBeUndefined();
        expect(next.metrics[1].description).toBeUndefined();
        expect(next.metrics[1].binding).toEqual({ dataset: 'fct__order', name: 'avg_price' });
    });

    it('leaves the other metrics untouched', () => {
        const next = updateMetric(graph, 'revenue', { label: 'Booked revenue' });

        expect(next.metrics[1]).toEqual(graph.metrics[1]);
    });
});

describe('unlinkMetric', () => {
    it('drops the binding and leaves an incomplete draft behind', () => {
        const graph = state([
            { id: 'avg_price', label: 'Avg price', binding: { dataset: 'fct__order', name: 'avg_price' } },
        ]);

        const next = unlinkMetric(graph, 'avg_price');

        expect(next.metrics[0].binding).toBeUndefined();
        expect(next.metrics[0].label).toBe('Avg price');
        expect(incompleteDraftIds(next.metrics)).toEqual(['avg_price']);
    });
});

describe('incompleteDraftIds', () => {
    it('names every draft without an expression', () => {
        expect(
            incompleteDraftIds([
                { id: 'a', label: 'A', expression: 'sum(x)' },
                { id: 'b', label: 'B', expression: '' },
                { id: 'c', label: 'C' },
                { id: 'd', label: 'D', expression: '   ' },
                { id: 'e', label: 'E', binding: { dataset: 'fct__order', name: 'e' } },
            ]),
        ).toEqual(['b', 'c', 'd']);
    });

    it('is empty for a canvas of complete drafts and bound entries', () => {
        expect(
            incompleteDraftIds([
                { id: 'a', label: 'A', expression: 'sum(x)' },
                { id: 'e', label: 'E', binding: { dataset: 'fct__order', name: 'e' } },
            ]),
        ).toEqual([]);
    });
});
