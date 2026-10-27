import { describe, expect, it } from 'vitest';
import type { MetricEntry, MetricInfluence } from '$lib/types';
import {
    METRIC_GRID,
    buildMetricEdges,
    buildMetricNodes,
    buildMetricTreePayload,
    influenceEdgeId,
    layoutFromMetrics,
    metricGridPosition,
    withMetricPosition,
} from './metric-graph';

function metric(id: string, extra: Partial<MetricEntry> = {}): MetricEntry {
    return { id, label: id, ...extra };
}

describe('metricGridPosition', () => {
    it('lays metrics out in deterministic rows instead of stacking them at the origin', () => {
        const positions = [0, 1, 2, 3].map((index) => metricGridPosition(index));

        expect(positions[0]).toEqual({ x: METRIC_GRID.originX, y: METRIC_GRID.originY });
        expect(positions[1].x).toBeGreaterThan(positions[0].x);
        expect(positions[1].y).toBe(positions[0].y);
        expect(positions[METRIC_GRID.columns].y).toBeGreaterThan(positions[0].y);

        positions.forEach((position) => {
            expect(position).not.toEqual({ x: 0, y: 0 });
        });
        expect(new Set(positions.map((position) => `${position.x}:${position.y}`)).size).toBe(4);
    });

    it('returns the same cell for the same index', () => {
        expect(metricGridPosition(5)).toEqual(metricGridPosition(5));
    });
});

describe('buildMetricNodes', () => {
    it('builds exactly one node per metric', () => {
        const nodes = buildMetricNodes([metric('revenue'), metric('order_count')], {});

        expect(nodes).toHaveLength(2);
        expect(nodes.map((node) => node.id)).toEqual(['revenue', 'order_count']);
        expect(nodes.every((node) => node.type === 'metric')).toBe(true);
        expect(nodes[0].data.metric.label).toBe('revenue');
    });

    it('prefers a stored layout position over the fallback grid', () => {
        const nodes = buildMetricNodes([metric('revenue'), metric('orders')], {
            orders: { x: 640, y: 320 },
        });

        expect(nodes[0].position).toEqual(metricGridPosition(0));
        expect(nodes[1].position).toEqual({ x: 640, y: 320 });
    });

    it('falls back to a metric position from the payload when the layout has none', () => {
        const nodes = buildMetricNodes([metric('revenue', { position: { x: 12, y: 34 } })], {});

        expect(nodes[0].position).toEqual({ x: 12, y: 34 });
    });

    it('gives every unstored metric a distinct position', () => {
        const nodes = buildMetricNodes([metric('a'), metric('b'), metric('c')], {});
        const keys = nodes.map((node) => `${node.position.x}:${node.position.y}`);

        expect(new Set(keys).size).toBe(3);
    });

    it('carries the unresolved flag from the payload onto the node data', () => {
        const nodes = buildMetricNodes([metric('revenue', { unresolved: true }), metric('orders')], {});

        expect(nodes[0].data.unresolved).toBe(true);
        expect(nodes[1].data.unresolved).toBe(false);
    });

    it('marks the selected metric when one is given', () => {
        const nodes = buildMetricNodes([metric('revenue'), metric('orders')], {}, 'orders');

        expect(nodes.map((node) => node.selected)).toEqual([false, true]);
    });
});

describe('buildMetricEdges', () => {
    const metrics = [metric('revenue'), metric('avg_price'), metric('order_count')];

    it('builds one edge per driver, pointing from the driver at the effect', () => {
        const influences: MetricInfluence[] = [
            { effect: 'revenue', drivers: ['avg_price', 'order_count'] },
        ];

        const edges = buildMetricEdges(metrics, influences);

        expect(edges).toHaveLength(2);
        expect(edges).toEqual([
            { id: influenceEdgeId('avg_price', 'revenue'), type: 'influence', source: 'avg_price', target: 'revenue' },
            { id: influenceEdgeId('order_count', 'revenue'), type: 'influence', source: 'order_count', target: 'revenue' },
        ]);
    });

    it('keeps edge ids stable and unique per driver-effect pair', () => {
        expect(influenceEdgeId('avg_price', 'revenue')).toBe(influenceEdgeId('avg_price', 'revenue'));
        expect(influenceEdgeId('avg_price', 'revenue')).not.toBe(influenceEdgeId('revenue', 'avg_price'));
    });

    it('drops repeated drivers and self-influences', () => {
        const edges = buildMetricEdges(metrics, [
            { effect: 'revenue', drivers: ['avg_price', 'avg_price', 'revenue'] },
        ]);

        expect(edges).toHaveLength(1);
        expect(edges[0].source).toBe('avg_price');
    });

    it('drops influences that reference a metric that is not on the canvas', () => {
        const edges = buildMetricEdges(metrics, [
            { effect: 'revenue', drivers: ['ghost'] },
            { effect: 'missing', drivers: ['revenue'] },
        ]);

        expect(edges).toEqual([]);
    });

    it('returns no edges for an empty influence list', () => {
        expect(buildMetricEdges(metrics, [])).toEqual([]);
    });
});

describe('layoutFromMetrics', () => {
    it('lifts stored positions into a layout keyed by metric id', () => {
        const layout = layoutFromMetrics([
            metric('revenue', { position: { x: 1, y: 2 } }),
            metric('orders'),
        ]);

        expect(layout).toEqual({ revenue: { x: 1, y: 2 } });
    });
});

describe('buildMetricTreePayload', () => {
    it('attaches the local layout position to every metric', () => {
        const payload = buildMetricTreePayload(
            {
                version: 0.1,
                metrics: [metric('revenue', { expression: 'sum(amount)' }), metric('orders', { expression: 'count(*)' })],
                influences: [{ effect: 'revenue', drivers: ['orders'] }],
            },
            { revenue: { x: 10, y: 20 } },
        );

        expect(payload.version).toBe(0.1);
        expect(payload.metrics[0].position).toEqual({ x: 10, y: 20 });
        expect(payload.metrics[1].position).toBeUndefined();
        expect(payload.influences).toEqual([{ effect: 'revenue', drivers: ['orders'] }]);
    });

    it('falls back to the position carried on the metric', () => {
        const payload = buildMetricTreePayload(
            { version: 0.1, metrics: [metric('revenue', { position: { x: 5, y: 6 } })], influences: [] },
            {},
        );

        expect(payload.metrics[0].position).toEqual({ x: 5, y: 6 });
    });

    it('strips the read-only unresolved flag before saving', () => {
        const payload = buildMetricTreePayload(
            { version: 0.1, metrics: [metric('revenue', { unresolved: true, expression: 'sum(x)' })], influences: [] },
            {},
        );

        expect(payload.metrics[0]).not.toHaveProperty('unresolved');
    });

    it('never sends an expression or description for a bound metric', () => {
        const payload = buildMetricTreePayload(
            {
                version: 0.1,
                metrics: [
                    {
                        id: 'avg_price',
                        label: 'Avg price',
                        binding: { dataset: 'fct__order', name: 'avg_price' },
                        description: 'stale copy',
                        expression: 'avg(amount)',
                    },
                ],
                influences: [],
            },
            {},
        );

        expect(payload.metrics[0]).toEqual({
            id: 'avg_price',
            label: 'Avg price',
            binding: { dataset: 'fct__order', name: 'avg_price' },
        });
    });

    it('keeps draft fields as they are', () => {
        const draft = {
            id: 'revenue',
            label: 'Revenue',
            description: 'Booked revenue.',
            expression: 'sum(amount)',
            dataset_ref: 'fct__order',
        };
        const payload = buildMetricTreePayload({ version: 0.1, metrics: [draft], influences: [] }, {});

        expect(payload.metrics[0]).toEqual(draft);
    });
});

describe('withMetricPosition', () => {
    it('records a dragged position against the metric id', () => {
        expect(withMetricPosition({}, 'revenue', { x: 120, y: 240 })).toEqual({
            revenue: { x: 120, y: 240 },
        });
    });

    it('moves only the dragged metric', () => {
        const layout = { revenue: { x: 0, y: 0 }, orders: { x: 10, y: 10 } };

        expect(withMetricPosition(layout, 'orders', { x: 99, y: 98 })).toEqual({
            revenue: { x: 0, y: 0 },
            orders: { x: 99, y: 98 },
        });
    });

    it('does not mutate the layout it was given', () => {
        const layout = { revenue: { x: 0, y: 0 } };
        withMetricPosition(layout, 'revenue', { x: 5, y: 5 });

        expect(layout.revenue).toEqual({ x: 0, y: 0 });
    });
});
