import { describe, expect, it } from 'vitest';
import type { MetricEntry, MetricInfluence } from '$lib/types';
import {
    METRIC_GRID,
    alignMetricLayout,
    buildMetricEdges,
    buildMetricNodes,
    buildMetricTreePayload,
    computeMetricLevels,
    influenceEdgeId,
    layoutFromMetrics,
    metricGridPosition,
    metricLevelY,
    snapMetricX,
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

    it('prefers a stored layout x position over the fallback grid while locking y to the tree level', () => {
        const nodes = buildMetricNodes([metric('revenue'), metric('orders')], {
            orders: { x: 640, y: 320 },
        });

        expect(nodes[0].position).toEqual(metricGridPosition(0));
        expect(nodes[1].position).toEqual({ x: 640, y: metricLevelY(0) });
    });

    it('falls back to a metric x position from the payload when the layout has none, with level-locked y', () => {
        const nodes = buildMetricNodes([metric('revenue', { position: { x: 10, y: 34 } })], {});

        expect(nodes[0].position).toEqual({ x: 10, y: metricLevelY(0) });
    });

    it('gives metrics on the same level of the tree the exact same y value and spaces them evenly around their effect node', () => {
        const metrics = [
            metric('sum_actual_billing', { position: { x: 500, y: 110 } }),
            metric('avg_billing_rate', { position: { x: 200, y: 255 } }),
            metric('sum_actual_billable_hours', { position: { x: 740, y: 295 } }),
        ];
        const influences: MetricInfluence[] = [
            {
                effect: 'sum_actual_billing',
                drivers: ['avg_billing_rate', 'sum_actual_billable_hours'],
            },
        ];

        const nodes = buildMetricNodes(metrics, {}, null, influences);
        const byId = Object.fromEntries(nodes.map((node) => [node.id, node.position]));

        expect(byId.sum_actual_billing.y).toBe(metricLevelY(0));
        expect(byId.avg_billing_rate.y).toBe(metricLevelY(1));
        expect(byId.sum_actual_billable_hours.y).toBe(metricLevelY(1));
        expect(byId.avg_billing_rate.y).toBe(byId.sum_actual_billable_hours.y);

        // Exact symmetric spacing around effect x=500: 500 - 150 = 350 and 500 + 150 = 650
        expect(byId.avg_billing_rate.x).toBe(350);
        expect(byId.sum_actual_billable_hours.x).toBe(650);
        expect((byId.avg_billing_rate.x + byId.sum_actual_billable_hours.x) / 2).toBe(
            byId.sum_actual_billing.x,
        );
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

    it('builds one edge per driver, connecting the effect at the top (source) to the driver below (target)', () => {
        const influences: MetricInfluence[] = [
            { effect: 'revenue', drivers: ['avg_price', 'order_count'] },
        ];

        const edges = buildMetricEdges(metrics, influences);

        expect(edges).toHaveLength(2);
        expect(edges).toEqual([
            { id: influenceEdgeId('avg_price', 'revenue'), type: 'influence', source: 'revenue', target: 'avg_price' },
            { id: influenceEdgeId('order_count', 'revenue'), type: 'influence', source: 'revenue', target: 'order_count' },
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
        expect(edges[0].source).toBe('revenue');
        expect(edges[0].target).toBe('avg_price');
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
    it('strips runtime positions so metric_tree.yml only holds definitions and influences', () => {
        const payload = buildMetricTreePayload(
            {
                version: 0.1,
                metrics: [
                    metric('revenue', { expression: 'sum(amount)', position: { x: 5, y: 6 } }),
                    metric('orders', { expression: 'count(*)' }),
                ],
                influences: [{ effect: 'revenue', drivers: ['orders'] }],
            },
            { revenue: { x: 10, y: 20 } },
        );

        expect(payload.version).toBe(0.1);
        expect(payload.metrics[0].position).toBeUndefined();
        expect(payload.metrics[1].position).toBeUndefined();
        expect(payload.influences).toEqual([{ effect: 'revenue', drivers: ['orders'] }]);
    });

    it('strips the read-only unresolved flag before saving', () => {
        const payload = buildMetricTreePayload(
            { version: 0.1, metrics: [metric('revenue', { unresolved: true, expression: 'sum(x)' })], influences: [] },
            {},
        );

        expect(payload.metrics[0]).not.toHaveProperty('unresolved');
    });

    it('strips the read-only resolved expression before saving', () => {
        const payload = buildMetricTreePayload(
            {
                version: 0.1,
                metrics: [
                    metric('revenue', {
                        expression: 'sum(x)',
                        resolved_expression: 'sum(amount)',
                    }),
                    {
                        id: 'avg_price',
                        label: 'Avg price',
                        binding: { dataset: 'fct__order', name: 'avg_price' },
                        resolved_expression: 'avg(amount)',
                    },
                ],
                influences: [],
            },
            {},
        );

        expect(payload.metrics[0]).not.toHaveProperty('resolved_expression');
        expect(payload.metrics[1]).toEqual({
            id: 'avg_price',
            label: 'Avg price',
            binding: { dataset: 'fct__order', name: 'avg_price' },
        });
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
    it('records a dragged position against the metric id and snaps x to the grid', () => {
        expect(withMetricPosition({}, 'revenue', { x: 123, y: 240 })).toEqual({
            revenue: { x: 120, y: 240 },
        });
    });

    it('moves only the dragged metric and snaps x to the grid', () => {
        const layout = { revenue: { x: 0, y: 0 }, orders: { x: 10, y: 10 } };

        expect(withMetricPosition(layout, 'orders', { x: 99, y: 98 })).toEqual({
            revenue: { x: 0, y: 0 },
            orders: { x: 100, y: 98 },
        });
    });

    it('locks y to the metric tree level and shifts the upstream effect when a driver is dragged horizontally', () => {
        const metrics = [metric('revenue', { position: { x: 300, y: 80 } }), metric('orders')];
        const influences: MetricInfluence[] = [{ effect: 'revenue', drivers: ['orders'] }];

        expect(
            withMetricPosition({}, 'orders', { x: 353, y: 999 }, metrics, influences),
        ).toEqual({
            revenue: { x: snapMetricX(353), y: metricLevelY(0) },
            orders: { x: snapMetricX(353), y: metricLevelY(1) },
        });
    });

    it('does not mutate the layout it was given', () => {
        const layout = { revenue: { x: 0, y: 0 } };
        withMetricPosition(layout, 'revenue', { x: 5, y: 5 });

        expect(layout.revenue).toEqual({ x: 0, y: 0 });
    });
});

describe('computeMetricLevels and alignMetricLayout', () => {
    it('assigns level 0 to roots and increments level for each driver layer', () => {
        const metrics = [
            metric('revenue'),
            metric('avg_price'),
            metric('order_count'),
            metric('base_price'),
        ];
        const influences: MetricInfluence[] = [
            { effect: 'revenue', drivers: ['avg_price', 'order_count'] },
            { effect: 'avg_price', drivers: ['base_price'] },
        ];

        const levels = computeMetricLevels(metrics, influences);
        expect(levels.get('revenue')).toBe(0);
        expect(levels.get('avg_price')).toBe(1);
        expect(levels.get('order_count')).toBe(1);
        expect(levels.get('base_price')).toBe(2);
    });

    it('aligns stored layout y coordinates to tree levels and spaces drivers evenly around their effect', () => {
        const metrics = [metric('revenue'), metric('orders'), metric('avg_price')];
        const influences: MetricInfluence[] = [
            { effect: 'revenue', drivers: ['orders', 'avg_price'] },
        ];
        const layout = {
            revenue: { x: 400, y: 80 },
            orders: { x: 300, y: 270 },
            avg_price: { x: 500, y: 80 },
        };

        const aligned = alignMetricLayout(metrics, influences, layout);
        expect(aligned.revenue).toEqual({ x: 400, y: metricLevelY(0) });
        expect(aligned.orders.y).toBe(metricLevelY(1));
        expect(aligned.avg_price.y).toBe(metricLevelY(1));
        expect(aligned.orders.x).toBe(250);
        expect(aligned.avg_price.x).toBe(550);
    });

    it('widens parent driver spacing when both drivers have their own subtrees so grandchildren never collide', () => {
        const metrics = [
            metric('sum_actual_billing', { position: { x: 480, y: 80 } }),
            metric('avg_billing_rate'),
            metric('sum_actual_billable_hours'),
            metric('delivery_pct'),
            metric('demand_pct'),
            metric('sum_allocated_hours'),
            metric('sum_available_hours'),
        ];
        const influences: MetricInfluence[] = [
            {
                effect: 'sum_actual_billing',
                drivers: ['avg_billing_rate', 'sum_actual_billable_hours'],
            },
            {
                effect: 'avg_billing_rate',
                drivers: ['delivery_pct', 'demand_pct'],
            },
            {
                effect: 'sum_actual_billable_hours',
                drivers: ['sum_allocated_hours', 'sum_available_hours'],
            },
        ];

        const aligned = alignMetricLayout(metrics, influences, {});

        // Root is centered between its two level-1 drivers (180 and 780 -> midpoint 480)
        expect(aligned.sum_actual_billing).toEqual({ x: 480, y: metricLevelY(0) });
        expect(aligned.avg_billing_rate).toEqual({ x: 180, y: metricLevelY(1) });
        expect(aligned.sum_actual_billable_hours).toEqual({ x: 780, y: metricLevelY(1) });

        // Each level-1 driver is centered between its own two level-2 drivers
        expect(aligned.delivery_pct).toEqual({ x: 30, y: metricLevelY(2) });
        expect(aligned.demand_pct).toEqual({ x: 330, y: metricLevelY(2) });
        expect(aligned.sum_allocated_hours).toEqual({ x: 630, y: metricLevelY(2) });
        expect(aligned.sum_available_hours).toEqual({ x: 930, y: metricLevelY(2) });
    });
});

describe('relatedMetricPosition', () => {
    it('places a driver below and an effect above the anchor metric', async () => {
        const { relatedMetricPosition } = await import('./metric-graph');
        const metrics = [metric('revenue', { position: { x: 400, y: 300 } })];

        const driverPos = relatedMetricPosition('revenue', 'driver', metrics, [], {});
        const effectPos = relatedMetricPosition('revenue', 'effect', metrics, [], {});

        expect(driverPos.y).toBeGreaterThan(300);
        expect(effectPos.y).toBeLessThan(300);
        expect(driverPos.x).toBe(400);
        expect(effectPos.x).toBe(400);
    });
});
