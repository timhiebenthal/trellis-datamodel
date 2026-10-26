import { describe, expect, it } from 'vitest';
import type { MetricEntry, MetricInfluence } from '$lib/types';
import { addDraftMetric, type MetricGraphState } from './metric-edits';

function state(
    metrics: MetricEntry[] = [],
    influences: MetricInfluence[] = [],
): MetricGraphState {
    return { metrics, influences };
}

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
        const existing = state([{ id: 'revenue', label: 'Revenue' }]);
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
        const existing = state(
            [{ id: 'revenue', label: 'Revenue' }, { id: 'orders', label: 'Orders' }],
            [{ effect: 'revenue', drivers: ['orders'] }],
        );

        const { state: next } = addDraftMetric(existing, 'Cost');

        expect(next.influences).toEqual([{ effect: 'revenue', drivers: ['orders'] }]);
        expect(existing.metrics).toHaveLength(2);
    });
});
