<script lang="ts">
    import {
        SvelteFlow,
        Controls,
        Background,
        BackgroundVariant,
        MiniMap,
        type Node,
        type Edge,
    } from "@xyflow/svelte";
    import { getLineage } from "$lib/api";
    import type { LineageResponse, LineageNode, LineageEdge } from "$lib/types";
    import Icon from "@iconify/svelte";
    import LineageSourceNode from "./LineageSourceNode.svelte";
    import LineageModelNode from "./LineageModelNode.svelte";
    import LineageLayerBandNode from "./LineageLayerBandNode.svelte";
    import LineageViewportSync from "./LineageViewportSync.svelte";
    import LineageEdgeComponent from "./LineageEdge.svelte";
    import { getConnectedNodeIds } from "$lib/edge-highlight-utils";

    const { open = false, modelId = null, onClose } = $props<{
        open: boolean;
        modelId: string | null;
        onClose: () => void;
    }>();

    let loading = $state(false);
    let error = $state<string | null>(null);
    let lineageData = $state<LineageResponse | null>(null);
    let lineageNodes = $state<Node[]>([]);
    let lineageEdges = $state<Edge[]>([]);
    let baseLineageEdges = $state<Edge[]>([]);
    let overlayEdges = $state<Edge[]>([]);
    let upstreamOfMap = new Map<string, string[]>();
    let visibleNodeIdsSet = new Set<string>();
    let nodeByIdMap = new Map<string, LineageNode>();
    let layerBoundsByLayer = $state<Record<string, { top: number; bottom: number }>>({});
    let layerBandMeta = $state<Array<{ id: string; bandX: number }>>([]);

    const nodeTypes = {
        source: LineageSourceNode,
        default: LineageModelNode, // Use custom node type for regular models
        layerBand: LineageLayerBandNode,
    };

    const edgeTypes = {
        default: LineageEdgeComponent,
    };

    // Edge type constant - use custom LineageEdge for all lineage edges
    const LINEAGE_EDGE_TYPE = "default";

    // Progressive display state (per-node expansion)
    // Rule: root + direct parents + all sources are always visible; everything else is collapsed by default.
    let expandedNodeIds = $state<Set<string>>(new Set());

    // SvelteFlow ref (for fitView after layout)
    let flowRef: any = null;
    let flowInitialized = false;

    // Fetch lineage when modal opens
    $effect(() => {
        if (open && modelId) {
            loadLineage();
        } else {
            // Reset state when modal closes
            lineageData = null;
            lineageNodes = [];
            lineageEdges = [];
            error = null;
            expandedNodeIds = new Set();
        }
    });

    async function loadLineage() {
        if (!modelId) return;

        loading = true;
        error = null;

        try {
            const data = await getLineage(modelId);
            if (!data) {
                error = "Model not found or lineage could not be generated.";
                return;
            }

            lineageData = data;
            updateGraphDisplay();
        } catch (e) {
            console.error("Error loading lineage:", e);
            error = e instanceof Error ? e.message : "Failed to load lineage";
        } finally {
            loading = false;
        }
    }

    function updateGraphDisplay() {
        if (!lineageData) return;

        const rootId = lineageData.metadata?.root_model_id ?? modelId ?? "";
        if (!rootId) return;

        // Preserve ALL existing node positions across progressive expansion updates
        // This prevents nodes from jumping around when new layers are added
        const existingPositions = new Map<string, { x: number; y: number }>();
        for (const n of lineageNodes) {
            // Skip layer bands - they need to recalculate to span the full width
            if (!String(n.id).startsWith('layer-band-')) {
                existingPositions.set(n.id, { x: n.position.x, y: n.position.y });
            }
        }

        // Build quick lookup maps
        const nodeById = new Map<string, LineageNode>();
        for (const n of lineageData.nodes) nodeById.set(n.id, n);
        nodeByIdMap = nodeById;

        // Build adjacency (upstream): target -> [sources]
        const upstreamOf = new Map<string, string[]>();
        for (const e of lineageData.edges) {
            const list = upstreamOf.get(e.target) ?? [];
            list.push(e.source);
            upstreamOf.set(e.target, list);
        }
        upstreamOfMap = upstreamOf;

        // Compute visible node IDs according to the rule
        const visibleNodeIds = new Set<string>();
        visibleNodeIds.add(rootId);

        // Direct parents (one hop upstream of root)
        const directParents = upstreamOf.get(rootId) ?? [];
        for (const up of directParents) visibleNodeIds.add(up);

        // Sources (always)
        const sources: string[] = [];
        for (const n of lineageData.nodes) {
            if (n.isSource) {
                visibleNodeIds.add(n.id);
                sources.push(n.id);
            }
        }

        // Expanded nodes: reveal one more hop upstream for that node
        const expandedParents: string[] = [];
        for (const expandedId of expandedNodeIds) {
            const upstreams = upstreamOf.get(expandedId) ?? [];
            for (const up of upstreams) {
                visibleNodeIds.add(up);
                expandedParents.push(up);
            }
        }
        

        // Track which nodes are visible vs ghosted (for styling)
        // All nodes will be rendered, but unexpanded ones will be ghosted
        const ghostedNodeIds = new Set<string>();
        for (const n of lineageData.nodes) {
            if (!visibleNodeIds.has(n.id)) {
                ghostedNodeIds.add(n.id);
            }
        }
        visibleNodeIdsSet = visibleNodeIds;


        // Filter to only visible nodes for layout calculation
        // Ghosted nodes will be added later for edge anchoring but won't affect layout
        const visibleLineageNodes = lineageData.nodes.filter((n) => visibleNodeIds.has(n.id));
        
        
        // All nodes (including ghosted) for edge creation
        const allLineageNodes = lineageData.nodes;

        // Check if layers are configured (any node has a layer field)
        const layersConfigured = visibleLineageNodes.some((n) => n.layer !== undefined);
        
        // Extract unique layers and compute layer ordering
        const layerOrder: string[] = [];
        const layerSet = new Set<string>();
        if (layersConfigured) {
            // Collect all layers from visible nodes
            for (const node of visibleLineageNodes) {
                if (node.layer) {
                    layerSet.add(node.layer);
                }
            }
            
            // Get configured layer order from metadata (if available)
            const configuredLayersOrder = lineageData.metadata?.lineage_layers ?? [];
            
            // Order: sources → configured layers (in config order) → unassigned
            if (layerSet.has("sources")) {
                layerOrder.push("sources");
            }
            
            // Add configured layers in their configured order (only if they exist in visible nodes)
            for (const layer of configuredLayersOrder) {
                if (layerSet.has(layer)) {
                    layerOrder.push(layer);
                }
            }
            
            if (layerSet.has("unassigned")) {
                layerOrder.push("unassigned");
            }
        }

        // Bucket visible nodes by layer (if configured) or by level (fallback)
        const layerBuckets = new Map<string, LineageNode[]>();
        const levelBuckets = new Map<number, LineageNode[]>();

        for (const node of visibleLineageNodes) {
            const levelSafe = node.level ?? 0;
            if (layersConfigured && node.layer) {
                const bucket = layerBuckets.get(node.layer) ?? [];
                bucket.push(node);
                layerBuckets.set(node.layer, bucket);
            } else {
                const bucket = levelBuckets.get(levelSafe) ?? [];
                bucket.push(node);
                levelBuckets.set(levelSafe, bucket);
            }
        }

        // Build per-layer vertical bounds in graph space (used for initial placement + drag clamping)
        // Dynamic height per layer so it adapts across projects and to progressive expansion.
        const LAYER_START_Y = 60;
        const LAYER_GAP = 24;
        const LAYER_MIN_HEIGHT = 140;
        const LAYER_MAX_HEIGHT = 520;
        const LAYER_HEADER_HEIGHT = 34; // space for label inside the band
        const LAYER_INNER_PADDING = 30;
        const LEVEL_SPACING_WITHIN_LAYER = 110; // more vertical breathing room within a layer

        const layerBounds = new Map<string, { top: number; bottom: number; height: number }>();
        if (layersConfigured) {
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
        }

        // Persist bounds for drag clamping
        layerBoundsByLayer = Object.fromEntries(
            [...layerBounds.entries()].map(([k, v]) => [k, { top: v.top, bottom: v.bottom }]),
        );

        // Precompute each node's sibling index and total at its level/layer
        const levelPositions = new Map<string, { index: number; count: number }>();
        
        if (layersConfigured) {
            // Group by layer, then by level within each layer
            for (const layer of layerOrder) {
                const layerNodes = layerBuckets.get(layer) ?? [];
                // Further bucket by level within layer
                const levelBucketsInLayer = new Map<number, LineageNode[]>();
                for (const node of layerNodes) {
                    const levelSafe = node.level ?? 0;
                    const bucket = levelBucketsInLayer.get(levelSafe) ?? [];
                    bucket.push(node);
                    levelBucketsInLayer.set(levelSafe, bucket);
                }
                // Assign positions within each level in the layer
                for (const [, nodes] of levelBucketsInLayer) {
                    const count = nodes.length;
                    nodes.forEach((n, idx) => levelPositions.set(n.id, { index: idx, count }));
                }
            }
        } else {
            // Original behavior: bucket by level only
            for (const [, nodes] of levelBuckets) {
                const count = nodes.length;
                nodes.forEach((n, idx) => levelPositions.set(n.id, { index: idx, count }));
            }
        }

        // Precompute hidden upstream info for visible nodes
        const hiddenInfoById = new Map<string, { hiddenCount: number; hiddenSources: string[] }>();

        function computeHiddenInfo(targetId: string): { hiddenCount: number; hiddenSources: string[] } {
            const hiddenNodes = new Set<string>();
            const hiddenSources = new Set<string>();
            const queue: string[] = [];
            const visited = new Set<string>();

            for (const up of upstreamOf.get(targetId) ?? []) queue.push(up);

            while (queue.length > 0) {
                const current = queue.shift();
                if (!current || visited.has(current)) continue;
                visited.add(current);

                if (visibleNodeIds.has(current)) {
                    const n = nodeById.get(current);
                    if (n?.isSource) hiddenSources.add(n.label ?? n.id);
                    continue;
                }

                hiddenNodes.add(current);
                for (const up of upstreamOf.get(current) ?? []) queue.push(up);
            }

            return { hiddenCount: hiddenNodes.size, hiddenSources: [...hiddenSources] };
        }

        for (const node of visibleLineageNodes) {
            hiddenInfoById.set(node.id, computeHiddenInfo(node.id));
        }

        // Build flow nodes for visible nodes first (they participate in layout)
        const visibleNodes: Node[] = [];
        for (const node of visibleLineageNodes) {
            const pos = levelPositions.get(node.id);
            const indexInLevel = pos?.index ?? 0;
            const countAtLevel = pos?.count ?? 1;
            visibleNodes.push(
                createFlowNode(
                    node,
                    indexInLevel,
                    countAtLevel,
                    layersConfigured,
                    layerOrder,
                    layerBuckets,
                    new Map(
                        [...layerBounds.entries()].map(([k, v]) => [k, { top: v.top, bottom: v.bottom }]),
                    ),
                    existingPositions,
                    false, // Not ghosted - these are visible nodes
                    hiddenInfoById.get(node.id),
                ),
            );
        }
        
        // Don't render ghosted nodes at all
        // The overlay edges (green edges) already handle showing connections through hidden paths
        // This keeps the graph clean and focused on the default visible set
        const ghostedNodes: Node[] = [];
        const ghostedLineageNodes: LineageNode[] = [];
        
        // Compute positions for ghosted nodes
        // We need to compute their level positions similar to visible nodes
        const ghostedLevelPositions = new Map<string, { index: number; count: number }>();
        
        if (layersConfigured) {
            // Group ghosted nodes by layer, then by level within each layer
            for (const layer of layerOrder) {
                const ghostedInLayer = ghostedLineageNodes.filter(n => n.layer === layer);
                const levelBucketsInLayer = new Map<number, LineageNode[]>();
                for (const node of ghostedInLayer) {
                    const levelSafe = node.level ?? 0;
                    const bucket = levelBucketsInLayer.get(levelSafe) ?? [];
                    bucket.push(node);
                    levelBucketsInLayer.set(levelSafe, bucket);
                }
                // Assign positions within each level in the layer
                for (const [, nodes] of levelBucketsInLayer) {
                    const count = nodes.length;
                    nodes.forEach((n, idx) => ghostedLevelPositions.set(n.id, { index: idx, count }));
                }
            }
        } else {
            // Original behavior: bucket by level only
            const ghostedLevelBuckets = new Map<number, LineageNode[]>();
            for (const node of ghostedLineageNodes) {
                const levelSafe = node.level ?? 0;
                const bucket = ghostedLevelBuckets.get(levelSafe) ?? [];
                bucket.push(node);
                ghostedLevelBuckets.set(levelSafe, bucket);
            }
            for (const [, nodes] of ghostedLevelBuckets) {
                const count = nodes.length;
                nodes.forEach((n, idx) => ghostedLevelPositions.set(n.id, { index: idx, count }));
            }
        }
        
        // For ghosted nodes, we need to compute approximate positions based on their level/layer
        // We'll use a simplified positioning that doesn't affect the main layout
        for (const ghostedNode of ghostedLineageNodes) {
            // Try to get position from existing nodes if it was manually positioned
            const existing = existingPositions.get(ghostedNode.id);
            
            // Compute approximate position based on level/layer if not already positioned
            if (!existing) {
                // Use the same positioning logic as visible nodes, but with ghosted level positions
                const pos = ghostedLevelPositions.get(ghostedNode.id);
                const indexInLevel = pos?.index ?? 0;
                const countAtLevel = pos?.count ?? 1;
                
                // Don't store position in existingPositions - let createFlowNode compute it
                // This ensures consistent positioning logic
            }
            
            const pos = ghostedLevelPositions.get(ghostedNode.id);
            const indexInLevel = pos?.index ?? 0;
            const countAtLevel = pos?.count ?? 1;
            
            const ghostedFlowNode = createFlowNode(
                ghostedNode,
                indexInLevel,
                countAtLevel,
                layersConfigured,
                layerOrder,
                layerBuckets,
                new Map(
                    [...layerBounds.entries()].map(([k, v]) => [k, { top: v.top, bottom: v.bottom }]),
                ),
                existingPositions,
                false, // isGhosted = false - render nodes as visible, only edges are ghosted
                undefined, // no hidden info for ghosted nodes
            );
            // Mark node as _notInDefaultView so fitView can exclude it
            ghostedFlowNode.data = { ...ghostedFlowNode.data, _notInDefaultView: true };
            ghostedNodes.push(ghostedFlowNode);
        }
        
        // Create edges for ALL nodes (visible and ghosted)
        // Edges connecting to/from ghosted nodes will be marked as ghosted
        const visibleEdges: Edge[] = [];
        const ghostedEdges: Edge[] = [];
        let skippedEdgesCount = 0;
        let skippedEdgesDetails: Array<{source: string, target: string, sourceVisible: boolean, targetVisible: boolean}> = [];
        
        // Iterate over all nodes (visible + ghosted) to create edges
        const allNodesForEdges = [...visibleLineageNodes, ...ghostedLineageNodes];
        
        for (const targetNode of allNodesForEdges) {
            const targetId = targetNode.id;
            const directUpstream = upstreamOf.get(targetId) ?? [];
            for (const upstreamId of directUpstream) {
                const sourceVisible = visibleNodeIds.has(upstreamId);
                const targetVisible = visibleNodeIds.has(targetId);
                const sourceGhosted = ghostedNodeIds.has(upstreamId);
                const targetGhosted = ghostedNodeIds.has(targetId);
                
                // Skip only if both endpoints are ghosted and neither is in the graph
                // Actually, we want to create edges if at least one endpoint is visible OR ghosted
                const edgeIsGhosted = sourceGhosted || targetGhosted;
                
                const edge = {
                    id: `edge-${upstreamId}-${targetId}`,
                    source: upstreamId,
                    target: targetId,
                    type: LINEAGE_EDGE_TYPE,
                    data: { _ghosted: edgeIsGhosted },
                };
                
                if (edgeIsGhosted) {
                    ghostedEdges.push(edge);
                } else {
                    visibleEdges.push(edge);
                }
            }
        }

        // Compute source overlays for nodes with hidden upstream
        const sourceOverlays: Edge[] = [];
        for (const node of visibleLineageNodes) {
            const hiddenInfo = hiddenInfoById.get(node.id);
            if (hiddenInfo && hiddenInfo.hiddenCount > 0) {
                sourceOverlays.push(...computeSourceOverlayEdges(node.id));
            }
        }
        
        overlayEdges = sourceOverlays;
        // Combine visible and ghosted nodes (ghosted nodes are added for edge anchoring)
        lineageNodes = [...visibleNodes, ...ghostedNodes];
        // Combine visible and ghosted edges
        baseLineageEdges = [...visibleEdges, ...ghostedEdges];
        lineageEdges = [...baseLineageEdges, ...overlayEdges];
        

        // Prepend background "layer band" nodes (graph-space), so they pan/zoom with everything else.
        if (layersConfigured && layerOrder.length > 0) {
            // Create an "infinite" horizontal strip that spans the entire canvas
            const xs = visibleNodes.map((n) => n.position.x);
            const minX = Math.min(...xs, 0);
            
            // Use massive width to create seamless infinite bands
            const BAND_WIDTH = 100000;
            const bandX = minX - 50000;

            const bandNodes: Node[] = layerOrder.map((layer) => {
                const bounds = layerBounds.get(layer);
                const top = bounds?.top ?? 0;
                const height = bounds?.height ?? 220;
                const label =
                    layer === "sources" ? "Sources" : layer === "unassigned" ? "Unassigned" : layer;
                return {
                    id: `layer-band-${layer}`,
                    type: "layerBand",
                    position: { x: bandX, y: top },
                    data: { label, width: BAND_WIDTH, height, labelX: 0 },
                    draggable: false,
                    selectable: false,
                    connectable: false,
                    focusable: false,
                    zIndex: -1, // Behind edges (which render at default ~0-5) and nodes (10+)
                };
            });

            // Ensure layer bands are behind edges and nodes
            // Order: layers (zIndex: -1) < edges (default ~0-5) < nodes (zIndex: 10+)
            // Include both visible and ghosted nodes
            lineageNodes = [
                ...bandNodes,
                ...visibleNodes.map((n) => ({ ...n, zIndex: n.zIndex ?? 10 })),
                ...ghostedNodes.map((n) => ({ ...n, zIndex: n.zIndex ?? 10 })),
            ];
            layerBandMeta = bandNodes.map((b) => ({ id: b.id as string, bandX }));
        } else {
            // Include both visible and ghosted nodes
            lineageNodes = [...visibleNodes, ...ghostedNodes];
            layerBandMeta = [];
        }

    // Fit view only on initial load (not on expansion)
        // On expansion, preserve the current viewport so users don't lose context
        if (!flowInitialized) {
            queueMicrotask(() => {
                try {
                    // Only fit visible nodes (not ghosted nodes or layer bands)
                    const fitNodes = lineageNodes.filter((n) => {
                        if (n.id.toString().startsWith("layer-band-")) return false;
                        // Exclude nodes not in default view (ghosted nodes)
                        const notInDefaultView = (n.data as any)?._notInDefaultView ?? false;
                        return !notInDefaultView;
                    });
                    
                    // Sample actual nodes being passed to SvelteFlow
                    const actualNodesSample = lineageNodes.filter(n => !String(n.id).startsWith("layer-band-")).slice(0, 3).map(n => ({
                        id: n.id,
                        type: n.type,
                        x: n.position.x,
                        y: n.position.y,
                        hidden: n.hidden,
                        draggable: n.draggable,
                        selectable: n.selectable,
                        ghosted: (n.data as any)?._ghosted,
                    }));
                    
                    flowRef?.fitView?.({
                        padding: 0.2,
                        nodes: fitNodes,
                    });
                    flowInitialized = true;
                    fetch("http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            location: "LineageModal.svelte:updateGraphDisplay",
                            message: "fitView invoked (initial load)",
                            data: {
                                fitNodesCount: fitNodes.length,
                                hasFlowRef: Boolean(flowRef),
                                actualNodesSample,
                                initialized: flowInitialized
                            },
                            timestamp: Date.now(),
                            sessionId: "debug-session",
                            runId: "run-ghost",
                            hypothesisId: "fit",
                        }),
                    }).catch(() => {});
                } catch (e) {
                    console.error("fitView error", e);
                }
            });
        }

        // Apply connected node highlighting based on current selection
        // Use microtask to ensure nodes are fully updated
        queueMicrotask(() => {
            applyConnectedNodeHighlighting();
        });
    }


    function createFlowNode(
        node: LineageNode,
        indexInLevel: number,
        countAtLevel: number,
        layersConfigured: boolean,
        layerOrder: string[],
        layerBuckets: Map<string, LineageNode[]>,
        layerBounds: Map<string, { top: number; bottom: number }>,
        existingPositions: Map<string, { x: number; y: number }>,
        isGhosted: boolean = false,
        hiddenInfo?: { hiddenCount: number; hiddenSources: string[] },
    ): Node {
        if (!lineageData) {
            return {
                id: node.id,
                type: node.isSource ? "source" : "default",
                position: { x: 0, y: 0 },
                data: {
                    label: node.label,
                    level: node.level,
                    isSource: node.isSource,
                },
            };
        }

        const H_SPACING = 260; // Horizontal spacing between siblings at the same level (use more width)
        const LEVEL_SPACING_WITHIN_LAYER = 110; // vertical spacing within a layer for different levels
        
        let yPosition: number;
        let xPosition: number;
        let extent: Node["extent"] | undefined;

        const existing = existingPositions.get(node.id);
        
        if (layersConfigured && node.layer) {
            // Layer-based positioning
            const layerIndex = layerOrder.indexOf(node.layer);
            const bounds = layerBounds.get(node.layer);
            const top = bounds?.top ?? 0;
            const bottom = bounds?.bottom ?? top + 200;
            const padding = 30;

            // If we have an existing position, use it AS-IS (don't clamp)
            // This preserves node positions when layers are added/removed
            if (existing) {
                yPosition = existing.y;
            } else if (layerIndex === -1) {
                yPosition = top + 40;
            } else {
                // Within layer, position by level (roughly centered)
                const layerNodes = layerBuckets.get(node.layer) ?? [];
                const levelsInLayer = new Set(layerNodes.map((n) => n.level));
                // Higher `level` = further upstream. We want parents above children,
                // so we place higher levels closer to the top of the band.
                const sortedLevels = Array.from(levelsInLayer).sort((a, b) => b - a);
                const levelIndexInLayer = Math.max(0, sortedLevels.indexOf(node.level));

                const baseY = top + 40;
                yPosition = baseY + levelIndexInLayer * LEVEL_SPACING_WITHIN_LAYER;
                
                // Only clamp NEW nodes (not existing ones)
                yPosition = Math.min(Math.max(yPosition, top + padding), bottom - padding);
            }

            // Hard constraint: prevent dragging outside of the layer band (works during drag)
            // Use a very wide X extent and the computed Y bounds.
            extent = [
                [-100000, top + padding],
                [100000, bottom - padding],
            ];
        } else {
            // Original level-based positioning (backward compatibility)
            const maxLevel = Math.max(...lineageData.nodes.map((n) => n.level ?? 0), 0);
            const BOTTOM_Y = 500;
            const TOP_Y = 80;
            const LEVEL_SPACING = 120;
            
            const levelSafe = node.level ?? 0;

            if (node.isSource) {
                yPosition = TOP_Y;
            } else if (levelSafe === 0) {
                yPosition = BOTTOM_Y;
            } else {
                yPosition = BOTTOM_Y - (levelSafe * LEVEL_SPACING);
            }
        }
        
        // X position: keep levels vertically aligned (no diagonal drift), but spread siblings.
        const siblingCenterOffset = (countAtLevel - 1) / 2;
        const siblingOffset = (indexInLevel - siblingCenterOffset) * H_SPACING;
        xPosition = existing?.x ?? siblingOffset;

        // Clamp X to a sane range to avoid huge off-screen layouts
        const CLAMP_X = 4000;
        if (xPosition > CLAMP_X) xPosition = CLAMP_X;
        if (xPosition < -CLAMP_X) xPosition = -CLAMP_X;
        
        return {
            id: node.id,
            type: node.isSource ? "source" : "default",
            position: { x: xPosition, y: yPosition },
            data: {
                label: node.label,
                level: node.level,
                isSource: node.isSource,
                sourceName: node.sourceName,
                layer: node.layer,
                _ghosted: isGhosted,
                _hiddenCount: hiddenInfo?.hiddenCount ?? 0,
                _hiddenSources: hiddenInfo?.hiddenSources ?? [],
                _expandHidden: () => expandNode(node.id),
            },
            zIndex: node.isSource ? 12 : node.level === 0 ? 15 : 10,
            extent,
            // Disable interactivity for ghosted nodes
            draggable: !isGhosted,
            selectable: !isGhosted,
        };
    }

    function handleNodeDragStop(event: { targetNode: Node | null; nodes: Node[]; event: MouseEvent | TouchEvent }) {
        // Enforce "node stays in its layer" by clamping Y to the band bounds.
        const dragged = event.targetNode;
        if (!dragged) return;

        // Ignore background band nodes
        if (typeof dragged.id === "string" && dragged.id.startsWith("layer-band-")) return;

        const layer = (dragged.data as any)?.layer as string | undefined;
        if (!layer) return;

        const bounds = layerBoundsByLayer[layer];
        if (!bounds) return;

        const padding = 30;
        const top = bounds.top;
        const bottom = bounds.bottom;
        const clampedY = Math.min(Math.max(dragged.position.y, top + padding), bottom - padding);

        lineageNodes = lineageNodes.map((n) => {
            if (n.id !== dragged.id) return n;
            return {
                ...n,
                position: { ...n.position, y: clampedY },
                data: { ...(n.data as any), __manualPosition: true },
            };
        });
    }

    function expandNode(nodeId: string) {
        expandedNodeIds = new Set([...expandedNodeIds, nodeId]);
        updateGraphDisplay();
    }

    // Compute and apply connected node highlighting
    // When nodes are selected, highlight their connected edges and connected nodes
    function applyConnectedNodeHighlighting() {
        // Get selected node IDs (excluding placeholders and layer bands)
        // Placeholders ("...") and layer bands should not trigger highlighting
        const selectedNodeIds = new Set<string>();
        for (const node of lineageNodes) {
            if (node.selected && !node.hidden) {
                const nodeId = String(node.id);
                // Exclude layer band background nodes
                if (node.type !== 'layerBand') {
                    selectedNodeIds.add(nodeId);
                }
            }
        }

        // If no nodes are selected, clear connected highlighting
        if (selectedNodeIds.size === 0) {
            lineageNodes = lineageNodes.map((node) => {
                const data = node.data as any;
                return {
                    ...node,
                    data: { ...data, _connectedToSelected: false },
                };
            });
            return;
        }

        // Get connected node IDs using utility function
        const getNode = (id: string) => {
            return lineageNodes.find((n) => String(n.id) === id);
        };

        const connectedNodeIds = getConnectedNodeIds(selectedNodeIds, lineageEdges, getNode);

        // Update nodes with connected state
        lineageNodes = lineageNodes.map((node) => {
            const nodeId = String(node.id);
            const isConnected = connectedNodeIds.has(nodeId);
            const data = node.data as any;
            return {
                ...node,
                data: { ...data, _connectedToSelected: isConnected },
            };
        });
    }

    // Handle node selection changes to update connected highlighting
    function handleNodesChange(changes: any) {

        // Check if any change affects selection
        const hasSelectionChange = changes.some((change: any) => 
            change.type === 'select' || change.type === 'position' && change.selected !== undefined
        );
        if (hasSelectionChange || changes.length > 0) {
            // Use a microtask to ensure nodes are updated
            queueMicrotask(() => {
                applyConnectedNodeHighlighting();
            });
        }
    }

    function computeSourceOverlayEdges(targetId: string): Edge[] {
        if (!upstreamOfMap.size || !nodeByIdMap.size) return [];
        const edges: Edge[] = [];
        const seenSources = new Set<string>();
        const queue: Array<{ id: string; hiddenSeen: boolean }> = [];
        const visited = new Set<string>();

        for (const up of upstreamOfMap.get(targetId) ?? []) {
            // Start with hiddenSeen = true only if that upstream is hidden
            queue.push({ id: up, hiddenSeen: !visibleNodeIdsSet.has(up) });
        }

        while (queue.length > 0) {
            const current = queue.shift();
            if (!current) break;
            const { id, hiddenSeen } = current;
            if (visited.has(id)) continue;
            visited.add(id);

            const node = nodeByIdMap.get(id);
            const isVisible = visibleNodeIdsSet.has(id);
            const isSource = node?.isSource === true;

            // Only add overlay if there was at least one hidden hop between target and this source
            if (isVisible && isSource && hiddenSeen) {
                if (!seenSources.has(id)) {
                    seenSources.add(id);
                    edges.push({
                        id: `overlay-${id}-${targetId}`,
                        source: id,
                        target: targetId,
                        type: LINEAGE_EDGE_TYPE,
                        data: { _overlay: true },
                    });
                }
                continue;
            }

            // Traverse further upstream only if not a source
            if (!isSource) {
                for (const up of upstreamOfMap.get(id) ?? []) {
                    const nextHidden = hiddenSeen || !visibleNodeIdsSet.has(up);
                    queue.push({ id: up, hiddenSeen: nextHidden });
                }
            }
        }

        // Fallback: if we know there are hidden upstreams (badge) but could not
        // resolve any source via hidden hops, connect to nearest visible upstream
        if (edges.length === 0) {
            for (const up of upstreamOfMap.get(targetId) ?? []) {
                if (!visibleNodeIdsSet.has(up)) continue;
                const upstreamNode = nodeByIdMap.get(up);
                if (upstreamNode?.isSource) {
                    edges.push({
                        id: `overlay-${up}-${targetId}`,
                        source: up,
                        target: targetId,
                        type: LINEAGE_EDGE_TYPE,
                        data: { _overlay: true },
                    });
                }
            }
        }

        return edges;
    }



    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onClose();
        }
    }

    function handleBackdropKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onClose();
        }
    }

    function handleEscapeKey(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onClose();
        }
    }

    // Listen for escape key
    $effect(() => {
        if (open) {
            window.addEventListener("keydown", handleEscapeKey);
            return () => {
                window.removeEventListener("keydown", handleEscapeKey);
            };
        }
    });

</script>

{#if open}
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        onclick={handleBackdropClick}
        onkeydown={handleBackdropKeydown}
        tabindex="-1"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lineage-modal-title"
    >
        <div
            class="bg-white rounded-xl shadow-2xl w-[94vw] h-[92vh] max-w-[1600px] max-h-[920px] border border-gray-200 flex flex-col"
        >
            <!-- Header -->
            <div class="px-5 py-4 flex items-center justify-between border-b border-gray-200 flex-shrink-0 relative z-40">
                <div class="flex items-center gap-2">
                    <Icon icon="lucide:git-branch" class="w-5 h-5 text-primary-600" />
                    <h2 id="lineage-modal-title" class="text-lg font-semibold text-gray-900">
                        Upstream Lineage
                    </h2>
                    {#if modelId}
                        <span class="text-sm text-gray-500 font-mono">{modelId}</span>
                    {/if}
                </div>
                <button
                    class="p-2 rounded-md hover:bg-gray-100 text-gray-700 hover:text-gray-900 transition-colors"
                    onclick={(e) => {
                        e.stopPropagation();
                        onClose();
                    }}
                    aria-label="Close"
                    title="Close (Esc)"
                >
                    <Icon icon="lucide:x" class="w-6 h-6 font-bold" />
                </button>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-hidden relative">
                {#if loading}
                    <div class="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                        <div class="flex flex-col items-center gap-3 text-gray-600">
                            <Icon icon="lucide:loader-2" class="w-8 h-8 animate-spin" />
                            <span class="text-sm">Generating lineage...</span>
                        </div>
                    </div>
                {:else if error}
                    <div class="p-5 flex flex-col items-center gap-4">
                        <div class="flex items-center gap-3 text-danger-700 bg-danger-50 border border-danger-200 rounded-lg px-4 py-3">
                            <Icon icon="lucide:alert-triangle" class="w-5 h-5" />
                            <span class="text-sm">{error}</span>
                        </div>
                        {#if error.includes("catalog") || error.includes("Catalog")}
                            <div class="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
                                <p class="font-medium mb-1">To generate lineage, you need to:</p>
                                <code class="block bg-white px-2 py-1 rounded border border-gray-300 mt-2">
                                    dbt docs generate
                                </code>
                            </div>
                        {/if}
                        <button
                            class="px-4 py-2 text-sm rounded-md bg-primary-600 text-white hover:bg-primary-700"
                            onclick={loadLineage}
                        >
                            Retry
                        </button>
                    </div>
                {:else if lineageData && lineageNodes.length > 0}
                    <SvelteFlow
                        bind:this={flowRef}
                        bind:nodes={lineageNodes}
                        edges={lineageEdges}
                        nodeTypes={nodeTypes}
                        edgeTypes={edgeTypes}
                        defaultEdgeOptions={{ type: LINEAGE_EDGE_TYPE }}
                        panOnDrag={true}
                        selectionOnDrag={false}
                        nodesDraggable={true}
                        nodesConnectable={false}
                        edgesSelectable={true}
                        onnodedragstop={handleNodeDragStop}
                        onnodeschange={handleNodesChange}
                        class="w-full h-full"
                    >
                        <Controls />
                        {#if layerBandMeta.length > 0}
                            <LineageViewportSync bands={layerBandMeta} />
                        {/if}
                        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
                        <MiniMap />
                    </SvelteFlow>
                {:else if lineageData}
                    <div class="p-5 text-center text-gray-500 text-sm">
                        No upstream dependencies found for this model.
                    </div>
                {/if}
            </div>

        </div>
    </div>
{/if}

