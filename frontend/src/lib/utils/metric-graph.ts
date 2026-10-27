import type { MetricEntry, MetricInfluence, MetricTreeEdge, MetricTreeNode, MetricTreeFile } from '$lib/types';

/**
 * Pure helpers behind the metric canvas.
 *
 * The metric canvas is a second canvas, not a mode of the entity canvas: it has
 * no groups, filters or star-schema positioning, and its state never touches the
 * `nodes`/`edges` stores. Everything here is a plain function of its arguments so
 * the graph can be reasoned about, and tested, without Svelte Flow or a browser.
 */

/** Where a metric sits on the canvas. Mirrors `position` in `metric_layout.yml`. */
export interface MetricPosition {
    x: number;
    y: number;
}

/** Positions keyed by metric id, as held by the page before a save. */
export type MetricLayout = Record<string, MetricPosition>;

/**
 * A metric node plus the runtime-only `selected` flag. `MetricTreeNode` in
 * `types.ts` stays the persisted/wire shape; selection is a canvas concern.
 */
export interface MetricCanvasNode extends MetricTreeNode {
    selected?: boolean;
}

/**
 * The violet accent. Dimensions are green and facts are blue, so metrics take a
 * third colour that cannot be mistaken for either: violet-500 as the line and
 * marker colour, violet-* utilities for the badges in `MetricNode.svelte`.
 */
export const METRIC_ACCENT = '#8b5cf6';

/**
 * Node-level actions the canvas publishes through Svelte context, so a node can
 * offer "remove" without widening `MetricNodeData` on the wire.
 */
export interface MetricCanvasActions {
    deleteMetric?: (metricId: string) => void;
}

/**
 * Geometry for metrics that arrive without a position. Deterministic: the same
 * index always lands in the same cell, so a reload never reshuffles the graph.
 */
export const METRIC_GRID = {
    originX: 80,
    originY: 80,
    columns: 3,
    columnWidth: 300,
    rowHeight: 190,
} as const;

/** The fallback cell for a metric at `index` in the document. */
export function metricGridPosition(index: number): MetricPosition {
    const safeIndex = Number.isFinite(index) && index > 0 ? Math.floor(index) : 0;
    const column = safeIndex % METRIC_GRID.columns;
    const row = Math.floor(safeIndex / METRIC_GRID.columns);

    return {
        x: METRIC_GRID.originX + column * METRIC_GRID.columnWidth,
        y: METRIC_GRID.originY + row * METRIC_GRID.rowHeight,
    };
}

/** Stable id for the edge a driver draws onto an effect. */
export function influenceEdgeId(driver: string, effect: string): string {
    return `influence:${driver}:${effect}`;
}

/** Positions already stored on the payload, keyed by metric id. */
export function layoutFromMetrics(metrics: MetricEntry[]): MetricLayout {
    const layout: MetricLayout = {};

    for (const entry of metrics) {
        if (entry.position) {
            layout[entry.id] = { x: entry.position.x, y: entry.position.y };
        }
    }

    return layout;
}

/**
 * One node per metric. A stored position wins, then a position carried on the
 * payload, then the grid cell for the metric's index - so nothing ever stacks
 * at `{0, 0}`.
 */
export function buildMetricNodes(
    metrics: MetricEntry[],
    layout: MetricLayout = {},
    selectedId: string | null = null,
): MetricCanvasNode[] {
    return metrics.map((entry, index) => {
        const stored = layout[entry.id] ?? entry.position;

        return {
            id: entry.id,
            type: 'metric',
            position: stored ? { x: stored.x, y: stored.y } : metricGridPosition(index),
            data: {
                metric: entry,
                unresolved: entry.unresolved ?? false,
            },
            selected: selectedId === entry.id,
        };
    });
}

/**
 * One directed edge per driver, from the driver to the effect. Repeated drivers
 * collapse, self-influences are dropped, and so is anything pointing at a metric
 * that is not on the canvas - the backend rejects those, so they can only arrive
 * from a hand-edited file.
 */
export function buildMetricEdges(
    metrics: MetricEntry[],
    influences: MetricInfluence[],
): MetricTreeEdge[] {
    const known = new Set(metrics.map((entry) => entry.id));
    const seen = new Set<string>();
    const edges: MetricTreeEdge[] = [];

    for (const influence of influences) {
        if (!known.has(influence.effect)) continue;

        for (const driver of influence.drivers) {
            if (driver === influence.effect || !known.has(driver)) continue;

            const id = influenceEdgeId(driver, influence.effect);
            if (seen.has(id)) continue;

            seen.add(id);
            edges.push({
                id,
                type: 'influence',
                source: driver,
                target: influence.effect,
            });
        }
    }

    return edges;
}

/**
 * The POST body. Positions travel on each metric and the backend splits them into
 * `metric_layout.yml`; `unresolved` is read-only server state and never sent back,
 * and a bound entry is reduced to its reference so a saved file can never hold a
 * copied definition.
 */
export function buildMetricTreePayload(
    tree: { version: number; metrics: MetricEntry[]; influences: MetricInfluence[] },
    layout: MetricLayout = {},
): MetricTreeFile {
    return {
        version: tree.version,
        metrics: tree.metrics.map((entry) => {
            const { unresolved: _unresolved, ...metric } = entry;
            const stored = layout[metric.id] ?? metric.position;

            if (metric.binding) {
                const { description: _description, expression: _expression, ...reference } = metric;
                return stored ? { ...reference, position: stored } : reference;
            }

            return stored ? { ...metric, position: stored } : metric;
        }),
        influences: tree.influences.map((influence) => ({
            effect: influence.effect,
            drivers: [...influence.drivers],
        })),
    };
}
