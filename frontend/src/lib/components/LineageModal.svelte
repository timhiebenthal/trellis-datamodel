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
    import { writable, get } from "svelte/store";
    import { getLineage } from "$lib/api";
    import type { LineageResponse } from "$lib/types";
    import {
        buildLineageGraph,
        highlightConnections,
        LAYER_BAND_PREFIX,
        LAYER_NODE_PADDING,
        LINEAGE_EDGE_TYPE,
        DEFAULT_EDGE_STYLE,
    } from "$lib/utils/lineage-graph";
    import Icon from "@iconify/svelte";
    import Modal from "./Modal.svelte";
    import LineageSourceNode from "./LineageSourceNode.svelte";
    import LineageModelNode from "./LineageModelNode.svelte";
    import LineagePlaceholderNode from "./LineagePlaceholderNode.svelte";
    import LineageLayerBandNode from "./LineageLayerBandNode.svelte";
    import LineageViewportSync from "./LineageViewportSync.svelte";

    const { open = false, modelId = null, onClose } = $props<{
        open: boolean;
        modelId: string | null;
        onClose: () => void;
    }>();

    let loading = $state(false);
    let error = $state<string | null>(null);
    let lineageData = $state<LineageResponse | null>(null);
    let lineageNodes = $state<Node[]>([]);
    // Use writable store for edges - SvelteFlow's internal reactivity works better with stores
    const lineageEdgesStore = writable<Edge[]>([]);
    let layerBoundsByLayer = $state<Record<string, { top: number; bottom: number }>>({});
    let layerBandMeta = $state<Array<{ id: string; bandX: number }>>([]);
    // Key to force SvelteFlow re-render when graph structure changes significantly
    let flowKey = $state(0);

    const nodeTypes = {
        source: LineageSourceNode,
        default: LineageModelNode, // Use custom node type for regular models
        placeholder: LineagePlaceholderNode,
        layerBand: LineageLayerBandNode,
    };

    // The {#key flowKey} wrapper ensures proper re-rendering on graph changes

    // Progressive display state (per-node expansion)
    // Rule: root + direct parents + all sources are always visible; everything else is collapsed by default.
    let expandedNodeIds = $state<Set<string>>(new Set());
    let selectedNodeId = $state<string | null>(null);

    // Fetch lineage when modal opens
    $effect(() => {
        if (open && modelId) {
            loadLineage();
        } else {
            // Reset state when modal closes
            lineageData = null;
            lineageNodes = [];
            lineageEdgesStore.set([]);
            error = null;
            expandedNodeIds = new Set();
            selectedNodeId = null;
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
            await updateGraphDisplay();
        } catch (e) {
            console.error("Error loading lineage:", e);
            error = e instanceof Error ? e.message : "Failed to load lineage";
        } finally {
            loading = false;
        }
    }


    async function updateGraphDisplay() {
        if (!lineageData) return;

        // Preserve user-adjusted positions across progressive expansion updates
        const existingPositions = new Map<string, { x: number; y: number }>();
        for (const n of lineageNodes) {
            // Only preserve positions for nodes the user has manually dragged.
            // Otherwise, allow layout recalculation to keep parents above children, etc.
            if ((n.data as any)?.__manualPosition === true) {
                existingPositions.set(n.id, { x: n.position.x, y: n.position.y });
            }
        }

        const graph = buildLineageGraph({
            data: lineageData,
            modelId,
            expandedNodeIds,
            existingPositions,
            onExpand: expandNode,
        });
        if (!graph) return;

        layerBoundsByLayer = graph.layerBoundsByLayer;
        layerBandMeta = graph.layerBandMeta;

        // Set nodes and edges SIMULTANEOUSLY - SvelteFlow needs both at once
        // Use store.set() for edges to ensure proper reactivity with SvelteFlow
        lineageNodes = graph.nodes;
        lineageEdgesStore.set([...graph.edges]);
        // Increment key to force SvelteFlow to re-render with new graph structure
        flowKey++;
        applyConnectionHighlight(selectedNodeId);
    }

    function handleNodeDragStop(event: { targetNode: Node | null; nodes: Node[]; event: MouseEvent | TouchEvent }) {
        // Enforce "node stays in its layer" by clamping Y to the band bounds.
        const dragged = event.targetNode;
        if (!dragged) return;

        // Ignore background band nodes
        if (typeof dragged.id === "string" && dragged.id.startsWith(LAYER_BAND_PREFIX)) return;

        const layer = (dragged.data as any)?.layer as string | undefined;
        if (!layer) return;

        const bounds = layerBoundsByLayer[layer];
        if (!bounds) return;

        const padding = LAYER_NODE_PADDING;
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

    async function expandNode(nodeId: string) {
        expandedNodeIds = new Set([...expandedNodeIds, nodeId]);
        await updateGraphDisplay();
    }

    function applyConnectionHighlight(selectedId: string | null) {
        const edges = get(lineageEdgesStore);
        if (edges.length === 0 || lineageNodes.length === 0) return;
        const styled = highlightConnections(
            lineageNodes,
            edges,
            selectedId,
            lineageData?.edges ?? [],
        );
        lineageEdgesStore.set(styled.edges);
        lineageNodes = styled.nodes;
    }

    function handleNodeClick(event: { node: Node }) {
        const nextSelected = event.node?.id?.toString() ?? null;
        if (nextSelected === selectedNodeId) return;
        selectedNodeId = nextSelected;
        applyConnectionHighlight(selectedNodeId);
    }

    function handlePaneClick() {
        if (!selectedNodeId) return;
        selectedNodeId = null;
        applyConnectionHighlight(selectedNodeId);
    }

</script>

<Modal
    {open}
    {onClose}
    class="bg-white rounded-xl shadow-2xl w-[94vw] h-[92vh] max-w-[1600px] max-h-[920px] border border-gray-200 flex flex-col"
    labelledBy="lineage-modal-title"
>
    <!-- Header -->
    <div class="px-5 py-4 flex items-center justify-between border-b border-gray-200 flex-shrink-0">
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
            onclick={onClose}
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
            {#key flowKey}
            <SvelteFlow
                bind:nodes={lineageNodes}
                edges={$lineageEdgesStore}
                nodeTypes={nodeTypes}
                defaultEdgeOptions={{
                    type: LINEAGE_EDGE_TYPE,
                    style: DEFAULT_EDGE_STYLE
                }}
                fitView
                fitViewOptions={{
                    // Only fit the nodes that are NOT background bands
                    nodes: lineageNodes.filter(n => !n.id.toString().startsWith('layer-band-')),
                    padding: 0.2
                }}
                panOnDrag={true}
                selectionOnDrag={false}
                nodesDraggable={true}
                nodesConnectable={false}
                onlyRenderVisibleElements={false}
                elevateEdgesOnSelect={true}
                onnodedragstop={handleNodeDragStop}
                onnodeclick={handleNodeClick}
                onpaneclick={handlePaneClick}
                class="w-full h-full"
            >
                <Controls />
                {#if layerBandMeta.length > 0}
                    <LineageViewportSync bands={layerBandMeta} />
                {/if}
                <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
                <MiniMap />
            </SvelteFlow>
            {/key}
        {:else if lineageData}
            <div class="p-5 text-center text-gray-500 text-sm">
                No upstream dependencies found for this model.
            </div>
        {/if}
    </div>

</Modal>

