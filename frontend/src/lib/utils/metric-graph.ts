import type {
    MetricCatalogEntry,
    MetricEntry,
    MetricInfluence,
    MetricTreeEdge,
    MetricTreeNode,
    MetricTreeFile,
} from '$lib/types';

/**
 * Pure helpers behind the metric canvas.
 *
 * The metric canvas is a second canvas, not a mode of the entity canvas: it has
 * no groups, filters or star-schema positioning, and its state never touches the
 * `nodes`/`edges` stores. Everything here is a plain function of its arguments so
 * the graph can be reasoned about, and tested, without Svelte Flow or a browser.
 */

/** Where a metric sits on the canvas. */
export interface MetricPosition {
    x: number;
    y: number;
}

/** Runtime positions keyed by metric id. */
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

export type MetricRelationKind = 'effect' | 'driver';

/**
 * Node-level actions the canvas publishes through Svelte context, so a node can
 * offer "remove" and "+ Add effect / + Add driver" without widening `MetricNodeData`
 * on the wire.
 */
export interface MetricCanvasActions {
    deleteMetric?: (metricId: string) => void;
    getMetrics?: () => MetricEntry[];
    getCatalog?: () => MetricCatalogEntry[];
    getInfluences?: () => MetricInfluence[];
    addRelatedDraft?: (anchorMetricId: string, relation: MetricRelationKind) => void;
    addRelatedCatalogMetric?: (
        anchorMetricId: string,
        relation: MetricRelationKind,
        entry: MetricCatalogEntry,
    ) => void;
    connectRelatedMetric?: (
        anchorMetricId: string,
        relation: MetricRelationKind,
        targetMetricId: string,
    ) => void;
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
    snapX: 10,
} as const;

const METRIC_NODE_MIN_GAP_X = 240;

/** Snap a horizontal coordinate to the metric canvas grid. */
export function snapMetricX(x: number): number {
    if (!Number.isFinite(x)) return METRIC_GRID.originX;
    const sign = x < 0 ? -1 : 1;
    const snapped = sign * Math.round(Math.abs(x) / METRIC_GRID.snapX) * METRIC_GRID.snapX;
    return Object.is(snapped, -0) ? 0 : snapped;
}

/** Fixed vertical coordinate for a 0-based tree depth level. */
export function metricLevelY(level: number): number {
    const safeLevel = Number.isFinite(level) && level > 0 ? Math.floor(level) : 0;
    return METRIC_GRID.originY + safeLevel * METRIC_GRID.rowHeight;
}

/**
 * Compute 0-based tree depth for each metric from `influences` (`effect` at top,
 * `drivers` below). Every driver sits at least one level below all of its effects,
 * and root effects whose only drivers sit deeper than level 1 are pulled down so
 * sibling effects of the same metric share a level row.
 */
export function computeMetricLevels(
    metrics: MetricEntry[],
    influences: MetricInfluence[] = [],
): Map<string, number> {
    const known = new Set(metrics.map((entry) => entry.id));
    const driversOf = new Map<string, string[]>();
    const inDegree = new Map<string, number>();
    const levels = new Map<string, number>();

    for (const entry of metrics) {
        driversOf.set(entry.id, []);
        inDegree.set(entry.id, 0);
        levels.set(entry.id, 0);
    }

    const seenEdges = new Set<string>();
    for (const influence of influences) {
        if (!known.has(influence.effect)) continue;
        for (const driver of influence.drivers) {
            if (driver === influence.effect || !known.has(driver)) continue;
            const edgeKey = `${influence.effect}->${driver}`;
            if (seenEdges.has(edgeKey)) continue;
            seenEdges.add(edgeKey);
            driversOf.get(influence.effect)!.push(driver);
            inDegree.set(driver, (inDegree.get(driver) ?? 0) + 1);
        }
    }

    const remainingInDegree = new Map(inDegree);
    const processed = new Set<string>();
    const queue: string[] = [];

    for (const entry of metrics) {
        if ((remainingInDegree.get(entry.id) ?? 0) === 0) {
            queue.push(entry.id);
        }
    }

    while (processed.size < metrics.length) {
        if (queue.length === 0) {
            const cycleStart = metrics.find((entry) => !processed.has(entry.id));
            if (!cycleStart) break;
            queue.push(cycleStart.id);
        }

        const current = queue.shift()!;
        if (processed.has(current)) continue;
        processed.add(current);

        const currentLevel = levels.get(current) ?? 0;
        for (const driver of driversOf.get(current) ?? []) {
            if (processed.has(driver)) continue;
            if ((levels.get(driver) ?? 0) < currentLevel + 1) {
                levels.set(driver, currentLevel + 1);
            }
            const nextIn = (remainingInDegree.get(driver) ?? 1) - 1;
            remainingInDegree.set(driver, nextIn);
            if (nextIn <= 0) {
                queue.push(driver);
            }
        }
    }

    // Tighten roots (no incoming effects) whose drivers all sit below level 1,
    // so multiple top-level effects of the same deep metric share the level above it.
    for (const entry of metrics) {
        if ((inDegree.get(entry.id) ?? 0) > 0) continue;
        const drivers = driversOf.get(entry.id) ?? [];
        if (drivers.length === 0) continue;
        const minDriverLevel = Math.min(...drivers.map((driver) => levels.get(driver) ?? 0));
        if (minDriverLevel > 1) {
            levels.set(entry.id, minDriverLevel - 1);
        }
    }

    return levels;
}

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

function isLevelXOccupied(occupiedX: number[], candidateX: number): boolean {
    return occupiedX.some((existingX) => Math.abs(existingX - candidateX) < METRIC_NODE_MIN_GAP_X);
}

function nextFreeLevelX(occupiedX: number[], preferredX?: number): number {
    if (preferredX !== undefined) {
        const snapped = snapMetricX(preferredX);
        if (!isLevelXOccupied(occupiedX, snapped)) {
            return snapped;
        }
        for (let step = 1; step <= occupiedX.length + 2; step++) {
            for (const dir of [1, -1]) {
                const candidate = snapMetricX(snapped + dir * step * METRIC_GRID.columnWidth);
                if (candidate >= 0 && !isLevelXOccupied(occupiedX, candidate)) {
                    return candidate;
                }
            }
        }
    }

    let col = 0;
    while (
        isLevelXOccupied(occupiedX, METRIC_GRID.originX + col * METRIC_GRID.columnWidth)
    ) {
        col += 1;
    }
    return METRIC_GRID.originX + col * METRIC_GRID.columnWidth;
}

function buildInfluenceMaps(
    metrics: MetricEntry[],
    influences: MetricInfluence[],
): {
    driversOf: Map<string, string[]>;
    effectsOf: Map<string, string[]>;
} {
    const known = new Set(metrics.map((entry) => entry.id));
    const driversOf = new Map<string, string[]>();
    const effectsOf = new Map<string, string[]>();

    for (const entry of metrics) {
        driversOf.set(entry.id, []);
        effectsOf.set(entry.id, []);
    }

    const seenEdges = new Set<string>();
    for (const influence of influences) {
        if (!known.has(influence.effect)) continue;
        for (const driver of influence.drivers) {
            if (driver === influence.effect || !known.has(driver)) continue;
            const edgeKey = `${influence.effect}->${driver}`;
            if (seenEdges.has(edgeKey)) continue;
            seenEdges.add(edgeKey);
            driversOf.get(influence.effect)!.push(driver);
            effectsOf.get(driver)!.push(influence.effect);
        }
    }

    return { driversOf, effectsOf };
}

function resolveMetricPositions(
    metrics: MetricEntry[],
    influences: MetricInfluence[],
    layout: MetricLayout,
): Map<string, MetricPosition> {
    const levels = computeMetricLevels(metrics, influences);
    const { driversOf, effectsOf } = buildInfluenceMaps(metrics, influences);

    const indexById = new Map<string, number>();
    metrics.forEach((entry, index) => indexById.set(entry.id, index));

    const storedX = new Map<string, number>();
    for (const entry of metrics) {
        const stored = layout[entry.id] ?? entry.position;
        if (stored && Number.isFinite(stored.x)) {
            storedX.set(entry.id, snapMetricX(stored.x));
        }
    }

    const byLevel = new Map<number, string[]>();
    let maxLevel = 0;
    for (const entry of metrics) {
        const level = levels.get(entry.id) ?? 0;
        if (level > maxLevel) maxLevel = level;
        const list = byLevel.get(level) ?? [];
        list.push(entry.id);
        byLevel.set(level, list);
    }

    const sortSiblings = (ids: string[]): string[] =>
        [...ids].sort((a, b) => {
            const ax = storedX.get(a);
            const bx = storedX.get(b);
            if (ax !== undefined && bx !== undefined && ax !== bx) {
                return ax - bx;
            }
            return (indexById.get(a) ?? 0) - (indexById.get(b) ?? 0);
        });

    // Assign each node to at most one primary parent on `level - 1` so subtree spans are well-defined.
    const treeChildren = new Map<string, string[]>();
    const primaryParent = new Map<string, string>();
    for (const entry of metrics) {
        treeChildren.set(entry.id, []);
    }

    for (let level = 0; level < maxLevel; level++) {
        const parents = sortSiblings(byLevel.get(level) ?? []);
        for (const parentId of parents) {
            const directDrivers = sortSiblings(
                (driversOf.get(parentId) ?? []).filter(
                    (driverId) =>
                        (levels.get(driverId) ?? 0) === level + 1 &&
                        !primaryParent.has(driverId),
                ),
            );
            treeChildren.set(parentId, directDrivers);
            for (const driverId of directDrivers) {
                primaryParent.set(driverId, parentId);
            }
        }
    }

    // Bottom-up pass: compute each node's per-level relative horizontal bounds `[min, max]`
    // and the symmetric offsets of its direct children so sibling subtrees never collide.
    const relBounds = new Map<string, Map<number, { min: number; max: number }>>();
    const childOffsets = new Map<string, Map<string, number>>();
    const stepQuantum = METRIC_GRID.snapX * 2;

    for (let level = maxLevel; level >= 0; level--) {
        for (const id of byLevel.get(level) ?? []) {
            const bounds = new Map<number, { min: number; max: number }>([
                [level, { min: 0, max: 0 }],
            ]);
            const offsets = new Map<string, number>();
            const children = treeChildren.get(id) ?? [];

            if (children.length > 0) {
                let step: number = METRIC_GRID.columnWidth;
                for (let i = 0; i < children.length; i++) {
                    const boundsI = relBounds.get(children[i]);
                    if (!boundsI) continue;
                    for (let j = i + 1; j < children.length; j++) {
                        const boundsJ = relBounds.get(children[j]);
                        if (!boundsJ) continue;
                        for (const [depth, rangeI] of boundsI) {
                            const rangeJ = boundsJ.get(depth);
                            if (!rangeJ) continue;
                            const needed =
                                (rangeI.max - rangeJ.min + METRIC_GRID.columnWidth) / (j - i);
                            if (needed > step) {
                                step = needed;
                            }
                        }
                    }
                }
                step = Math.ceil(step / stepQuantum) * stepQuantum;

                const count = children.length;
                children.forEach((childId, idx) => {
                    const offset = snapMetricX((idx - (count - 1) / 2) * step);
                    offsets.set(childId, offset);
                    const childMap = relBounds.get(childId);
                    if (!childMap) return;
                    for (const [depth, range] of childMap) {
                        const existing = bounds.get(depth);
                        const min = offset + range.min;
                        const max = offset + range.max;
                        if (existing) {
                            existing.min = Math.min(existing.min, min);
                            existing.max = Math.max(existing.max, max);
                        } else {
                            bounds.set(depth, { min, max });
                        }
                    }
                });
            }

            relBounds.set(id, bounds);
            childOffsets.set(id, offsets);
        }
    }

    const resolvedX = new Map<string, number>();
    const occupiedByLevel = new Map<number, number[]>();

    for (let level = 0; level <= maxLevel; level++) {
        const idsOnLevel = byLevel.get(level) ?? [];
        const occupied = occupiedByLevel.get(level) ?? [];

        // 1. Place children of parents from `level - 1` using their exact symmetric offsets.
        if (level > 0) {
            const parentIds = [...(byLevel.get(level - 1) ?? [])].sort(
                (a, b) =>
                    (resolvedX.get(a) ?? 0) - (resolvedX.get(b) ?? 0) ||
                    (indexById.get(a) ?? 0) - (indexById.get(b) ?? 0),
            );

            for (const parentId of parentIds) {
                const parentX = resolvedX.get(parentId) ?? METRIC_GRID.originX;
                const offsets = childOffsets.get(parentId);
                for (const childId of treeChildren.get(parentId) ?? []) {
                    if (resolvedX.has(childId)) continue;
                    const desiredX = snapMetricX(parentX + (offsets?.get(childId) ?? 0));
                    const x = nextFreeLevelX(occupied, desiredX);
                    occupied.push(x);
                    resolvedX.set(childId, x);
                }
            }
        }

        // 2. Place remaining nodes on this level (roots, or multi-level edges).
        for (const id of idsOnLevel) {
            if (resolvedX.has(id)) continue;
            const parentXs = (effectsOf.get(id) ?? [])
                .map((effectId) => resolvedX.get(effectId))
                .filter((val): val is number => val !== undefined);

            if (parentXs.length > 0) {
                const avgParentX =
                    parentXs.reduce((sum, val) => sum + val, 0) / parentXs.length;
                const x = nextFreeLevelX(occupied, snapMetricX(avgParentX));
                occupied.push(x);
                resolvedX.set(id, x);
            } else if (storedX.has(id)) {
                const x = storedX.get(id)!;
                occupied.push(x);
                resolvedX.set(id, x);
            } else {
                const bounds = relBounds.get(id);
                const minRel = bounds
                    ? Math.min(...Array.from(bounds.values()).map((b) => b.min))
                    : 0;
                const preferredRootX = snapMetricX(METRIC_GRID.originX - minRel);
                const x = nextFreeLevelX(occupied, preferredRootX);
                occupied.push(x);
                resolvedX.set(id, x);
            }
        }

        occupiedByLevel.set(level, occupied);
    }

    const resolved = new Map<string, MetricPosition>();
    for (const entry of metrics) {
        const level = levels.get(entry.id) ?? 0;
        const x = resolvedX.get(entry.id) ?? METRIC_GRID.originX;
        const y = metricLevelY(level);
        resolved.set(entry.id, { x, y });
    }

    return resolved;
}

/** Stable id for the edge a driver draws onto an effect. */
export function influenceEdgeId(driver: string, effect: string): string {
    return `influence:${driver}:${effect}`;
}

/**
 * Compute a clean position for a new related metric above (`effect`) or below (`driver`)
 * `anchorMetricId`, spreading multiple drivers/effects horizontally around the anchor.
 */
export function relatedMetricPosition(
    anchorMetricId: string,
    relation: MetricRelationKind,
    metrics: MetricEntry[],
    influences: MetricInfluence[],
    layout: MetricLayout,
): MetricPosition {
    const anchorIndex = metrics.findIndex((entry) => entry.id === anchorMetricId);
    const anchorMetric = anchorIndex >= 0 ? metrics[anchorIndex] : undefined;
    const resolved = resolveMetricPositions(metrics, influences, layout);
    const anchorPos =
        layout[anchorMetricId] ??
        anchorMetric?.position ??
        resolved.get(anchorMetricId) ??
        metricGridPosition(anchorIndex >= 0 ? anchorIndex : 0);

    const siblingCount =
        relation === 'driver'
            ? (influences.find((inf) => inf.effect === anchorMetricId)?.drivers.length ?? 0)
            : influences.filter((inf) => inf.drivers.includes(anchorMetricId)).length;

    const horizontalStep = METRIC_GRID.columnWidth;
    const verticalStep = METRIC_GRID.rowHeight;
    const offsetIndex =
        siblingCount === 0
            ? 0
            : (siblingCount % 2 === 1 ? 1 : -1) * Math.ceil(siblingCount / 2);

    const levels = computeMetricLevels(metrics, influences);
    const anchorLevel = levels.get(anchorMetricId) ?? 0;
    const targetLevel = relation === 'driver' ? anchorLevel + 1 : Math.max(0, anchorLevel - 1);
    const occupiedOnTargetLevel: number[] = [];
    for (const entry of metrics) {
        if (entry.id === anchorMetricId && relation === 'effect' && anchorLevel === 0) continue;
        if ((levels.get(entry.id) ?? 0) === targetLevel) {
            const pos = resolved.get(entry.id);
            if (pos) occupiedOnTargetLevel.push(pos.x);
        }
    }

    const desiredX = snapMetricX(anchorPos.x + offsetIndex * horizontalStep);
    const x = nextFreeLevelX(occupiedOnTargetLevel, desiredX);

    return {
        x,
        y: anchorPos.y + (relation === 'driver' ? verticalStep : -verticalStep),
    };
}

/**
 * Align stored positions in `layout` so every metric's `y` matches its tree level
 * and every driver is spaced evenly and symmetrically in `x` around its effect node.
 */
export function alignMetricLayout(
    metrics: MetricEntry[],
    influences: MetricInfluence[],
    layout: MetricLayout,
): MetricLayout {
    const resolved = resolveMetricPositions(metrics, influences, layout);
    const next: MetricLayout = {};

    for (const entry of metrics) {
        const pos = resolved.get(entry.id);
        if (pos) {
            next[entry.id] = { x: pos.x, y: pos.y };
        }
    }

    return next;
}

/**
 * Record a dragged node's position in the local layout. The save payload reads
 * from here, so a drag survives the next save without a reload. When `metrics`
 * is provided, `y` is locked to the metric's tree level, `x` snaps to the grid,
 * and dragging a driver horizontally shifts its upstream root effect so all
 * sibling drivers stay evenly spaced around their effect.
 */
export function withMetricPosition(
    layout: MetricLayout,
    metricId: string,
    position: MetricPosition,
    metrics: MetricEntry[] = [],
    influences: MetricInfluence[] = [],
): MetricLayout {
    const levels = computeMetricLevels(metrics, influences);
    const level = levels.get(metricId);
    const snappedX = snapMetricX(position.x);
    const y = level !== undefined ? metricLevelY(level) : position.y;
    const updated: MetricLayout = { ...layout, [metricId]: { x: snappedX, y } };

    if (metrics.length > 0 && influences.length > 0) {
        const before = resolveMetricPositions(metrics, influences, layout);
        for (const [id, pos] of before) {
            if (!updated[id]) {
                updated[id] = { x: pos.x, y: pos.y };
            }
        }
        updated[metricId] = { x: snappedX, y };

        const prevPos = before.get(metricId);
        if (prevPos && prevPos.x !== snappedX) {
            const deltaX = snappedX - prevPos.x;
            const { driversOf, effectsOf } = buildInfluenceMaps(metrics, influences);
            const directParents = effectsOf.get(metricId) ?? [];
            const hasSiblings = directParents.some(
                (parentId) => (driversOf.get(parentId)?.length ?? 0) > 1,
            );

            // Only shift the upstream root when dragging an single-child chain; when a
            // driver has siblings, dragging it horizontally reorders it among its siblings
            // while keeping the effect node anchored.
            if (!hasSiblings) {
                const visited = new Set<string>([metricId]);
                const queue = [...directParents];

                while (queue.length > 0) {
                    const current = queue.shift()!;
                    if (visited.has(current)) continue;
                    visited.add(current);
                    const parents = effectsOf.get(current) ?? [];
                    if (parents.length === 0) {
                        const rootPos = before.get(current);
                        if (rootPos) {
                            updated[current] = {
                                x: snapMetricX(rootPos.x + deltaX),
                                y: rootPos.y,
                            };
                        }
                    } else {
                        queue.push(...parents);
                    }
                }
            }
        }
        return alignMetricLayout(metrics, influences, updated);
    }

    return updated;
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
 * One node per metric. Each node's `y` coordinate is locked to its tree depth
 * level (`computeMetricLevels`) so metrics on the same level always share the
 * exact same row, while `x` comes from the stored layout or the next free column
 * on that level.
 */
export function buildMetricNodes(
    metrics: MetricEntry[],
    layout: MetricLayout = {},
    selectedId: string | null = null,
    influences: MetricInfluence[] = [],
): MetricCanvasNode[] {
    const resolved = resolveMetricPositions(metrics, influences, layout);

    return metrics.map((entry, index) => {
        const position = resolved.get(entry.id) ?? metricGridPosition(index);

        return {
            id: entry.id,
            type: 'metric',
            position: { x: position.x, y: position.y },
            data: {
                metric: entry,
                unresolved: entry.unresolved ?? false,
            },
            selected: selectedId === entry.id,
        };
    });
}

/**
 * One edge per driver, connecting the bottom handle of the upper `effect` node
 * (`source`) to the top handle of the lower `driver` node (`target`). Repeated
 * drivers collapse, self-influences are dropped, and so is anything pointing at
 * a metric that is not on the canvas.
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
                source: influence.effect,
                target: driver,
            });
        }
    }

    return edges;
}

/**
 * The POST body. `position`, `unresolved` and `resolved_expression` are runtime or
 * read-only state and never sent back, and a bound entry is reduced to its
 * reference so a saved file can never hold a copied definition.
 */
export function buildMetricTreePayload(
    tree: { version: number; metrics: MetricEntry[]; influences: MetricInfluence[] },
    _layout: MetricLayout = {},
): MetricTreeFile {
    return {
        version: tree.version,
        metrics: tree.metrics.map((entry) => {
            const {
                position: _position,
                unresolved: _unresolved,
                resolved_expression: _resolvedExpression,
                ...metric
            } = entry;

            if (metric.binding) {
                const { description: _description, expression: _expression, ...reference } = metric;
                return reference;
            }

            return metric;
        }),
        influences: tree.influences.map((influence) => ({
            effect: influence.effect,
            drivers: [...influence.drivers],
        })),
    };
}
