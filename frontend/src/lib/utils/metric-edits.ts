import type { MetricEntry, MetricInfluence } from '$lib/types';
import { generateSlug } from '$lib/utils';

/**
 * Graph edits for the metric canvas, as pure functions over `{ metrics, influences }`.
 *
 * The page owns the document and hands each edit the current state; every helper
 * returns a new state and never mutates its argument. Keeping the rules here (and
 * not in the components) is what makes "no duplicate influence" and "delete the
 * entry when its last driver goes" testable without a browser.
 */

export interface MetricGraphState {
    metrics: MetricEntry[];
    influences: MetricInfluence[];
}

export const NEW_METRIC_LABEL = 'New metric';

export interface AddedMetric {
    state: MetricGraphState;
    metric: MetricEntry;
}

/**
 * Create a hand-authored metric. The id comes from the label through
 * `generateSlug`, which also guarantees it is unique against the canvas.
 */
export function addDraftMetric(
    state: MetricGraphState,
    label: string = NEW_METRIC_LABEL,
): AddedMetric {
    const cleanLabel = label.trim() || NEW_METRIC_LABEL;
    const id = generateSlug(cleanLabel, state.metrics.map((entry) => entry.id));

    const metric: MetricEntry = {
        id,
        label: cleanLabel,
        description: '',
        expression: '',
    };

    return {
        state: { ...state, metrics: [...state.metrics, metric] },
        metric,
    };
}
