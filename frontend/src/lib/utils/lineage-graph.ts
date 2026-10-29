import type { Edge, Node } from '@xyflow/svelte';
import type { LineageEdge, LineageNode, LineageResponse } from '$lib/types';

/**
 * Pure graph construction behind the lineage modal.
 *
 * Given the raw lineage response, the set of expanded nodes and any positions the
 * user dragged by hand, these functions produce the Svelte Flow nodes and edges.
 * No stores, no I/O: the modal owns state and rendering, this owns the maths.
 */

export const LINEAGE_EDGE_TYPE = 'bezier';
export const DEFAULT_EDGE_STYLE = 'stroke: #94a3b8; stroke-width: 2;';
export const HIGHLIGHT_EDGE_STYLE =
    'stroke: #2dd4bf; stroke-width: 3.25; filter: drop-shadow(0 0 4px rgba(13, 148, 136, 0.3));';
export const DIM_EDGE_STYLE = DEFAULT_EDGE_STYLE;
export const CONNECTED_NODE_CLASS = 'ring-2 ring-primary-400';

export const LAYER_BAND_PREFIX = 'layer-band-';
export const PLACEHOLDER_PREFIX = 'placeholder-';

/** Vertical room kept between a node and the edge of its layer band. */
export const LAYER_NODE_PADDING = 30;

export interface LayerBounds {
    top: number;
    bottom: number;
}

export interface LayerBandMeta {
    id: string;
    bandX: number;
}

export interface LineageGraph {
    nodes: Node[];
    edges: Edge[];
    layerBoundsByLayer: Record<string, LayerBounds>;
    layerBandMeta: LayerBandMeta[];
}

export interface BuildLineageGraphOptions {
    data: LineageResponse;
    /** Fallback root when the response metadata carries none. */
    modelId: string | null;
    /** Nodes whose upstream has been expanded by the user. */
    expandedNodeIds: Set<string>;
    /** Positions of nodes the user dragged, kept across rebuilds. */
    existingPositions: Map<string, { x: number; y: number }>;
    /** Called with the target node id when a `...` placeholder is clicked. */
    onExpand: (targetId: string) => void;
}

/** target -> [sources] adjacency of the raw lineage edges. */
export function buildUpstreamMap(edges: LineageEdge[]): Map<string, string[]> {
    const upstreamOf = new Map<string, string[]>();
    for (const e of edges) {
        const list = upstreamOf.get(e.target) ?? [];
        list.push(e.source);
        upstreamOf.set(e.target, list);
    }
    return upstreamOf;
}

/**
 * Progressive display rule: root + direct parents + all sources are always
 * visible; everything else is collapsed until an upstream hop is expanded.
 */
export function computeVisibleNodeIds(
    data: LineageResponse,
    rootId: string,
    expandedNodeIds: Set<string>,
    upstreamOf: Map<string, string[]>,
): Set<string> {
    const visible = new Set<string>();
    visible.add(rootId);

    for (const up of upstreamOf.get(rootId) ?? []) visible.add(up);

    for (const n of data.nodes) {
        if (n.isSource) visible.add(n.id);
    }

    for (const expandedId of expandedNodeIds) {
        for (const up of upstreamOf.get(expandedId) ?? []) visible.add(up);
    }

    return visible;
}

/** Order: sources, then configured layers (in config order), then unassigned. */
function computeLayerOrder(visibleNodes: LineageNode[], configuredOrder: string[]): string[] {
    const layerSet = new Set<string>();
    for (const node of visibleNodes) {
        if (node.layer) layerSet.add(node.layer);
    }

    const layerOrder: string[] = [];
    if (layerSet.has('sources')) layerOrder.push('sources');
    for (const layer of configuredOrder) {
        if (layerSet.has(layer)) layerOrder.push(layer);
    }
    if (layerSet.has('unassigned')) layerOrder.push('unassigned');
    return layerOrder;
}

function bucketBy<K>(
    nodes: LineageNode[],
    keyOf: (node: LineageNode) => K,
    buckets: Map<K, LineageNode[]> = new Map(),
): Map<K, LineageNode[]> {
    for (const node of nodes) {
        const key = keyOf(node);
        const bucket = buckets.get(key) ?? [];
        bucket.push(node);
        buckets.set(key, bucket);
    }
    return buckets;
}

const LAYER_START_Y = 60;
const LAYER_GAP = 24;
const LAYER_MIN_HEIGHT = 140;
const LAYER_MAX_HEIGHT = 520;
const LAYER_HEADER_HEIGHT = 34; // space for label inside the band
const LAYER_INNER_PADDING = 30;
const LEVEL_SPACING_WITHIN_LAYER = 110; // vertical breathing room between levels in a layer

/** Dynamic per-layer vertical bounds, so bands adapt to content and expansion. */
function computeLayerBounds(
    layerOrder: string[],
    layerBuckets: Map<string, LineageNode[]>,
): Map<string, { top: number; bottom: number; height: number }> {
    const layerBounds = new Map<string, { top: number; bottom: number; height: number }>();
    let cursorY = LAYER_START_Y;
    for (const layer of layerOrder) {
        const nodesInLayer = layerBuckets.get(layer) ?? [];
        const levelsInLayer = new Set(nodesInLayer.map((n) => n.level));
        const levelCount = Math.max(1, levelsInLayer.size);

        const contentHeight =
            LAYER_HEADER_HEIGHT +
            LAYER_INNER_PADDING * 2 +
            (levelCount - 1) * LEVEL_SPACING_WITHIN_LAYER;

        const height = Math.max(LAYER_MIN_HEIGHT, Math.min(LAYER_MAX_HEIGHT, contentHeight));
        const top = cursorY;
        const bottom = top + height;
        layerBounds.set(layer, { top, bottom, height });
        cursorY = bottom + LAYER_GAP;
    }
    return layerBounds;
}

/** Each node's sibling index and total at its level (within its layer, when layered). */
function computeLevelPositions(
    layersConfigured: boolean,
    layerOrder: string[],
    layerBuckets: Map<string, LineageNode[]>,
    levelBuckets: Map<number, LineageNode[]>,
): Map<string, { index: number; count: number }> {
    const levelPositions = new Map<string, { index: number; count: number }>();
    const assign = (nodes: LineageNode[]) => {
        const count = nodes.length;
        nodes.forEach((n, idx) => levelPositions.set(n.id, { index: idx, count }));
    };

    if (layersConfigured) {
        for (const layer of layerOrder) {
            const byLevel = bucketBy(layerBuckets.get(layer) ?? [], (n) => n.level);
            for (const [, nodes] of byLevel) assign(nodes);
        }
    } else {
        for (const [, nodes] of levelBuckets) assign(nodes);
    }
    return levelPositions;
}

function createFlowNode(
    node: LineageNode,
    indexInLevel: number,
    countAtLevel: number,
    layersConfigured: boolean,
    layerOrder: string[],
    layerBuckets: Map<string, LineageNode[]>,
    layerBounds: Map<string, LayerBounds>,
    existingPositions: Map<string, { x: number; y: number }>,
): Node {
    const H_SPACING = 260; // horizontal spacing between siblings at the same level

    let yPosition: number;
    let extent: Node['extent'] | undefined;

    const existing = existingPositions.get(node.id);

    if (layersConfigured && node.layer) {
        const layerIndex = layerOrder.indexOf(node.layer);
        const bounds = layerBounds.get(node.layer);
        const top = bounds?.top ?? 0;
        const bottom = bounds?.bottom ?? top + 200;

        // A user-dragged position wins (but is clamped to the band below)
        if (existing) {
            yPosition = existing.y;
        } else if (layerIndex === -1) {
            yPosition = top + 40;
        } else {
            // Within the layer, position by level (roughly centered)
            const layerNodes = layerBuckets.get(node.layer) ?? [];
            const levelsInLayer = new Set(layerNodes.map((n) => n.level));
            // Higher `level` = further upstream. Parents go above children,
            // so higher levels sit closer to the top of the band.
            const sortedLevels = Array.from(levelsInLayer).sort((a, b) => b - a);
            const levelIndexInLayer = Math.max(0, sortedLevels.indexOf(node.level));

            const baseY = top + 40;
            yPosition = baseY + levelIndexInLayer * LEVEL_SPACING_WITHIN_LAYER;
        }

        yPosition = Math.min(
            Math.max(yPosition, top + LAYER_NODE_PADDING),
            bottom - LAYER_NODE_PADDING,
        );

        // Hard constraint: keep the node in its layer band while dragging.
        extent = [
            [-100000, top + LAYER_NODE_PADDING],
            [100000, bottom - LAYER_NODE_PADDING],
        ];
    } else {
        // Level-based positioning (no layers configured)
        const BOTTOM_Y = 500;
        const TOP_Y = 80;
        const LEVEL_SPACING = 120;

        if (node.isSource) {
            yPosition = TOP_Y;
        } else if (node.level === 0) {
            yPosition = BOTTOM_Y;
        } else {
            yPosition = BOTTOM_Y - node.level * LEVEL_SPACING;
        }
    }

    // X: keep levels vertically aligned (no diagonal drift), but spread siblings.
    const siblingCenterOffset = (countAtLevel - 1) / 2;
    const siblingOffset = (indexInLevel - siblingCenterOffset) * H_SPACING;
    const xPosition = existing?.x ?? siblingOffset;

    return {
        id: node.id,
        type: node.isSource ? 'source' : 'default',
        position: { x: xPosition, y: yPosition },
        width: node.isSource ? 160 : 150,
        height: node.isSource ? 60 : 36,
        data: {
            label: node.label,
            level: node.level,
            isSource: node.isSource,
            sourceName: node.sourceName,
            layer: node.layer,
        },
        zIndex: node.isSource ? 12 : node.level === 0 ? 15 : 10,
        extent,
    };
}

/**
 * Build the visible Svelte Flow graph for the current expansion state.
 * Returns null when there is no root to anchor the graph on.
 */
export function buildLineageGraph(options: BuildLineageGraphOptions): LineageGraph | null {
    const { data, modelId, expandedNodeIds, existingPositions, onExpand } = options;

    const rootId = data.metadata?.root_model_id ?? modelId ?? '';
    if (!rootId) return null;

    const nodeById = new Map<string, LineageNode>();
    for (const n of data.nodes) nodeById.set(n.id, n);

    const upstreamOf = buildUpstreamMap(data.edges);
    const visibleNodeIds = computeVisibleNodeIds(data, rootId, expandedNodeIds, upstreamOf);
    const visibleLineageNodes = data.nodes.filter((n) => visibleNodeIds.has(n.id));

    // Layers are configured when any node carries a layer field
    const layersConfigured = visibleLineageNodes.some((n) => n.layer !== undefined);
    const layerOrder = layersConfigured
        ? computeLayerOrder(visibleLineageNodes, data.metadata?.lineage_layers ?? [])
        : [];

    // Bucket visible nodes by layer (if configured) or by level (fallback)
    const layerBuckets = new Map<string, LineageNode[]>();
    const levelBuckets = new Map<number, LineageNode[]>();
    for (const node of visibleLineageNodes) {
        if (layersConfigured && node.layer) {
            bucketBy([node], () => node.layer as string, layerBuckets);
        } else {
            bucketBy([node], (n) => n.level, levelBuckets);
        }
    }

    const layerBounds = layersConfigured
        ? computeLayerBounds(layerOrder, layerBuckets)
        : new Map<string, { top: number; bottom: number; height: number }>();
    const layerBoundsByLayer: Record<string, LayerBounds> = Object.fromEntries(
        [...layerBounds.entries()].map(([k, v]) => [k, { top: v.top, bottom: v.bottom }]),
    );

    const levelPositions = computeLevelPositions(
        layersConfigured,
        layerOrder,
        layerBuckets,
        levelBuckets,
    );

    const visibleNodes: Node[] = [];
    for (const node of visibleLineageNodes) {
        const pos = levelPositions.get(node.id);
        visibleNodes.push(
            createFlowNode(
                node,
                pos?.index ?? 0,
                pos?.count ?? 1,
                layersConfigured,
                layerOrder,
                layerBuckets,
                new Map(Object.entries(layerBoundsByLayer)),
                existingPositions,
            ),
        );
    }

    // Placeholders + edge compression:
    // If hidden intermediate models exist between two visible nodes, route via a `...`
    // placeholder attached to the downstream visible node, keeping the graph connected
    // without pretending it's a direct edge.
    const visibleEdges: Edge[] = [];
    const placeholderIdByTarget = new Map<string, string>();
    const placeholderToTargetEdgeAdded = new Set<string>();
    const placeholderUpstreamsByTarget = new Map<string, Set<string>>();

    function ensurePlaceholder(targetId: string): string | null {
        const targetFlowNode = visibleNodes.find((n) => n.id === targetId);
        if (!targetFlowNode) return null;

        const existing = placeholderIdByTarget.get(targetId);
        if (existing) return existing;

        const placeholderId = `${PLACEHOLDER_PREFIX}${targetId}`;
        placeholderIdByTarget.set(targetId, placeholderId);

        visibleNodes.push({
            id: placeholderId,
            type: 'placeholder',
            position: {
                x: targetFlowNode.position.x,
                // Temporary; repositioned once the upstream connections are known.
                y: targetFlowNode.position.y,
            },
            width: 120,
            height: 32,
            data: {
                label: '...',
                onClick: () => onExpand(targetId),
                // Keep placeholder in the same layer as its target (for band clamping)
                layer: nodeById.get(targetId)?.layer as string | undefined,
            },
            zIndex: 20,
        });

        return placeholderId;
    }

    function getNearestVisibleUpstream(
        targetId: string,
    ): Array<{ upstreamId: string; depth: number }> {
        const results = new Map<string, number>();
        const queue: Array<{ id: string; depth: number }> = [];
        const visited = new Set<string>();

        for (const up of upstreamOf.get(targetId) ?? []) {
            queue.push({ id: up, depth: 1 });
        }

        while (queue.length > 0) {
            const current = queue.shift();
            if (!current) break;
            const { id, depth } = current;
            if (visited.has(id)) continue;
            visited.add(id);

            if (visibleNodeIds.has(id)) {
                const existing = results.get(id);
                if (existing === undefined || depth < existing) results.set(id, depth);
                continue; // stop at first visible node on this path
            }

            for (const up of upstreamOf.get(id) ?? []) {
                queue.push({ id: up, depth: depth + 1 });
            }
        }

        return [...results.entries()].map(([upstreamId, depth]) => ({ upstreamId, depth }));
    }

    for (const targetNode of visibleLineageNodes) {
        const targetId = targetNode.id;

        if (targetId.startsWith(PLACEHOLDER_PREFIX)) continue;
        if (!nodeById.has(targetId)) continue;

        for (const { upstreamId, depth } of getNearestVisibleUpstream(targetId)) {
            if (depth === 1) {
                visibleEdges.push({
                    id: `edge-${upstreamId}-${targetId}`,
                    source: upstreamId,
                    target: targetId,
                    type: LINEAGE_EDGE_TYPE,
                    zIndex: 5, // Edges render above layer bands (zIndex: -1)
                    style: DEFAULT_EDGE_STYLE,
                });
                continue;
            }

            const placeholderId = ensurePlaceholder(targetId);
            if (!placeholderId) continue;

            const upstreamSet = placeholderUpstreamsByTarget.get(targetId) ?? new Set<string>();
            upstreamSet.add(upstreamId);
            placeholderUpstreamsByTarget.set(targetId, upstreamSet);

            visibleEdges.push({
                id: `edge-${upstreamId}-${placeholderId}`,
                source: upstreamId,
                target: placeholderId,
                type: LINEAGE_EDGE_TYPE,
                zIndex: 5,
                style: DEFAULT_EDGE_STYLE,
            });

            const key = `${placeholderId}=>${targetId}`;
            if (!placeholderToTargetEdgeAdded.has(key)) {
                placeholderToTargetEdgeAdded.add(key);
                visibleEdges.push({
                    id: `edge-${placeholderId}-${targetId}`,
                    source: placeholderId,
                    target: targetId,
                    type: LINEAGE_EDGE_TYPE,
                    zIndex: 5,
                    style: DEFAULT_EDGE_STYLE,
                });
            }
        }
    }

    // Move each placeholder halfway between its upstream(s) and its target, which
    // reduces the "curl" near the target when edges converge.
    for (const [targetId, upstreamIds] of placeholderUpstreamsByTarget) {
        const placeholderId = placeholderIdByTarget.get(targetId);
        if (!placeholderId) continue;

        const targetFlowNode = visibleNodes.find((n) => n.id === targetId);
        const placeholderFlowNode = visibleNodes.find((n) => n.id === placeholderId);
        if (!targetFlowNode || !placeholderFlowNode) continue;

        const upstreamYs: number[] = [];
        const upstreamXs: number[] = [];
        for (const upId of upstreamIds) {
            const upNode = visibleNodes.find((n) => n.id === upId);
            if (upNode) {
                upstreamYs.push(upNode.position.y);
                upstreamXs.push(upNode.position.x);
            }
        }
        if (upstreamYs.length === 0) continue;

        // Use the highest upstream Y to keep the placeholder above the target
        // even when upstreams differ.
        const minUpstreamY = Math.min(...upstreamYs);
        const avgUpstreamX = upstreamXs.reduce((sum, x) => sum + x, 0) / upstreamXs.length;

        placeholderFlowNode.position = {
            x: Math.round((avgUpstreamX + targetFlowNode.position.x) / 2),
            y: Math.round((minUpstreamY + targetFlowNode.position.y) / 2),
        };
    }

    // Placeholders also stay inside their layer band
    if (layersConfigured) {
        for (const n of visibleNodes) {
            if (typeof n.id !== 'string' || !n.id.startsWith(PLACEHOLDER_PREFIX)) continue;
            const layer = (n.data as { layer?: string } | undefined)?.layer;
            if (!layer) continue;
            const bounds = layerBounds.get(layer);
            if (!bounds) continue;
            n.extent = [
                [-100000, bounds.top + LAYER_NODE_PADDING],
                [100000, bounds.bottom - LAYER_NODE_PADDING],
            ];
        }
    }

    // Prepend background "layer band" nodes (graph-space), so they pan/zoom with everything else.
    if (layersConfigured && layerOrder.length > 0) {
        const xs = visibleNodes.map((n) => n.position.x);
        const minX = Math.min(...xs, 0);
        const maxX = Math.max(...xs, 0);

        // Width based on the actual node spread (with generous padding) avoids massive
        // DOM elements that can interfere with edge visibility calculations.
        const BAND_PADDING = 2000;
        const BAND_WIDTH = Math.max(5000, maxX - minX + BAND_PADDING * 2);
        const bandX = minX - BAND_PADDING;

        const bandNodes: Node[] = layerOrder.map((layer) => {
            const bounds = layerBounds.get(layer);
            const top = bounds?.top ?? 0;
            const height = bounds?.height ?? 220;
            const label =
                layer === 'sources' ? 'Sources' : layer === 'unassigned' ? 'Unassigned' : layer;
            return {
                id: `${LAYER_BAND_PREFIX}${layer}`,
                type: 'layerBand',
                position: { x: bandX, y: top },
                data: { label, width: BAND_WIDTH, height, labelX: 0 },
                draggable: false,
                selectable: false,
                connectable: false,
                focusable: false,
                zIndex: -1, // Behind edges (~0-5) and nodes (10+)
            };
        });

        return {
            nodes: [...bandNodes, ...visibleNodes.map((n) => ({ ...n, zIndex: n.zIndex ?? 10 }))],
            edges: visibleEdges,
            layerBoundsByLayer,
            layerBandMeta: bandNodes.map((b) => ({ id: b.id as string, bandX })),
        };
    }

    return {
        nodes: visibleNodes,
        edges: visibleEdges,
        layerBoundsByLayer,
        layerBandMeta: [],
    };
}

/**
 * Style the graph for the current selection: highlight the selected node's full
 * upstream closure (computed from the raw lineage, not just visible edges) and
 * dim every other edge. With no selection everything returns to the default look.
 */
export function highlightConnections(
    nodes: Node[],
    edges: Edge[],
    selectedId: string | null,
    lineageEdges: LineageEdge[],
): { nodes: Node[]; edges: Edge[] } {
    if (!selectedId) {
        return {
            edges: edges.map((edge) => ({ ...edge, style: DEFAULT_EDGE_STYLE })),
            nodes: nodes.map((node) => {
                if (typeof node.id === 'string' && node.id.startsWith(LAYER_BAND_PREFIX)) return node;
                return { ...node, class: undefined, style: 'opacity: 1;' };
            }),
        };
    }

    const connectedEdgeIds = new Set<string>();
    const connectedNodeIds = new Set<string>();
    const upstreamOf = buildUpstreamMap(lineageEdges);

    const queue: string[] = [selectedId];
    while (queue.length > 0) {
        const current = queue.shift();
        if (!current || connectedNodeIds.has(current)) continue;
        connectedNodeIds.add(current);
        for (const up of upstreamOf.get(current) ?? []) {
            if (!connectedNodeIds.has(up)) queue.push(up);
        }
    }

    for (const edge of edges) {
        const sourceId = edge.source.toString();
        const targetId = edge.target.toString();
        const sourceInSet = connectedNodeIds.has(sourceId);
        const targetInSet = connectedNodeIds.has(targetId);

        if (sourceInSet && targetInSet) {
            connectedEdgeIds.add(edge.id);
            continue;
        }

        const isPlaceholderSource = sourceId.startsWith(PLACEHOLDER_PREFIX);
        const isPlaceholderTarget = targetId.startsWith(PLACEHOLDER_PREFIX);
        if ((sourceInSet && isPlaceholderTarget) || (targetInSet && isPlaceholderSource)) {
            connectedEdgeIds.add(edge.id);
            connectedNodeIds.add(isPlaceholderSource ? sourceId : targetId);
        }
    }

    return {
        edges: edges.map((edge) => ({
            ...edge,
            style: connectedEdgeIds.has(edge.id) ? HIGHLIGHT_EDGE_STYLE : DIM_EDGE_STYLE,
        })),
        nodes: nodes.map((node) => {
            if (typeof node.id === 'string' && node.id.startsWith(LAYER_BAND_PREFIX)) return node;
            const isConnected = connectedNodeIds.has(node.id.toString());
            return {
                ...node,
                class: isConnected ? CONNECTED_NODE_CLASS : undefined,
                style: 'opacity: 1;',
            };
        }),
    };
}
