<script lang="ts">
    import {
        SvelteFlow,
        Controls,
        Background,
        BackgroundVariant,
        MarkerType,
        type Connection,
        type Edge,
        type Node,
    } from "@xyflow/svelte";
    import { setContext } from "svelte";
    import Icon from "$lib/components/Icon.svelte";
    import MetricNode from "./MetricNode.svelte";
    import MetricInfluenceEdge from "./MetricInfluenceEdge.svelte";
    import type { MetricEntry, MetricInfluence } from "$lib/types";
    import {
        METRIC_ACCENT,
        buildMetricEdges,
        buildMetricNodes,
        type MetricCanvasActions,
        type MetricLayout,
    } from "$lib/utils/metric-graph";

    /**
     * The metric canvas. It is deliberately not `Canvas.svelte`: no groups, no
     * filters, no lineage, no star-schema positioner, and no reads of the global
     * `nodes`/`edges` stores. Everything it draws comes from the props below, and
     * every mutation is handed back to the page as a callback.
     */
    let {
        metrics = [],
        influences = [],
        layout = {},
        selectedMetricId = null,
        onaddmetric,
        onselectmetric,
        onconnect,
        ondeleteedge,
        ondeletemetric,
        onmove,
    }: {
        metrics?: MetricEntry[];
        influences?: MetricInfluence[];
        layout?: MetricLayout;
        selectedMetricId?: string | null;
        onaddmetric?: () => void;
        onselectmetric?: (metricId: string | null) => void;
        /** Drag source is the driver, drag target is the effect. */
        onconnect?: (driver: string, effect: string) => void;
        ondeleteedge?: (driver: string, effect: string) => void;
        ondeletemetric?: (metricId: string) => void;
        /** A node was dropped: the page records its new position. */
        onmove?: (metricId: string, position: { x: number; y: number }) => void;
    } = $props();

    const nodeTypes = { metric: MetricNode };
    const edgeTypes = { influence: MetricInfluenceEdge };

    // Node-level actions travel through context so `MetricNodeData` stays the
    // wire shape it is on the server.
    setContext<MetricCanvasActions>("metricCanvas", {
        deleteMetric: (metricId: string) => ondeletemetric?.(metricId),
    });

    const flowNodes = $derived(
        buildMetricNodes(metrics, layout, selectedMetricId) as unknown as Node[],
    );

    const flowEdges = $derived(
        buildMetricEdges(metrics, influences).map((edge) => ({
            ...edge,
            // Directed claim: the arrow points at the metric that moves.
            markerEnd: {
                type: MarkerType.ArrowClosed,
                width: 16,
                height: 16,
                color: METRIC_ACCENT,
            },
        })) as unknown as Edge[],
    );

    const isEmpty = $derived(metrics.length === 0);

    function handleConnect(connection: Connection) {
        if (!connection.source || !connection.target) return;
        onconnect?.(connection.source, connection.target);
    }

    function handleDelete({ nodes: goneNodes, edges: goneEdges }: { nodes: Node[]; edges: Edge[] }) {
        for (const edge of goneEdges ?? []) {
            ondeleteedge?.(edge.source, edge.target);
        }
        for (const node of goneNodes ?? []) {
            ondeletemetric?.(node.id);
        }
    }

    function handleNodeClick({ node }: { node: Node }) {
        onselectmetric?.(node.id);
    }

    function handlePaneClick() {
        onselectmetric?.(null);
    }

    /**
     * Report where a node was dropped. The canvas does not keep that position
     * itself: the page owns the layout, so the save payload and the rendered
     * position can never disagree.
     */
    function handleNodeDragStop({ targetNode }: { targetNode: Node | null }) {
        if (!targetNode || !onmove) return;
        onmove(targetNode.id, { x: targetNode.position.x, y: targetNode.position.y });
    }

    /** A metric cannot drive itself, and the same arrow only exists once. */
    function isValidConnection(connection: Connection | Edge): boolean {
        if (!connection.source || !connection.target) return false;
        if (connection.source === connection.target) return false;

        return !influences.some(
            (influence) =>
                influence.effect === connection.target &&
                influence.drivers.includes(connection.source as string),
        );
    }
</script>

<div class="relative h-full w-full flex-1 bg-slate-50">
    {#if isEmpty}
        <div class="flex h-full w-full items-center justify-center px-6">
            <div
                class="max-w-md rounded-xl border border-slate-200 bg-white/90 p-8 text-center shadow-sm"
                data-testid="metric-canvas-empty"
            >
                <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-violet-50">
                    <Icon icon="lucide:network" class="h-8 w-8 text-violet-600" />
                </div>
                <h3 class="text-xl font-semibold text-slate-800">Nothing to explain yet</h3>
                <p class="mt-2 text-sm leading-relaxed text-slate-600">
                    A metric tree answers one question: why did this number move. Add two
                    metrics, then draw an arrow from the one you suspect to the one you watch.
                </p>
                {#if onaddmetric}
                    <button
                        type="button"
                        class="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-[#0f172a] px-6 py-2.5 font-medium text-white shadow-md transition-colors hover:bg-slate-800"
                        onclick={onaddmetric}
                        data-testid="metric-canvas-empty-cta"
                    >
                        <Icon icon="lucide:plus" class="h-4 w-4" />
                        Add your first metric
                    </button>
                {/if}
            </div>
        </div>
    {:else}
        <SvelteFlow
            nodes={flowNodes}
            edges={flowEdges}
            {nodeTypes}
            {edgeTypes}
            fitView
            fitViewOptions={{ padding: 0.3, maxZoom: 1 }}
            panOnDrag
            selectionOnDrag={false}
            onlyRenderVisibleElements
            onconnect={handleConnect}
            ondelete={handleDelete}
            onnodeclick={handleNodeClick}
            onpaneclick={handlePaneClick}
            onnodedragstop={handleNodeDragStop}
            isValidConnection={isValidConnection}
            class="bg-slate-50"
        >
            <Controls />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        </SvelteFlow>

        {#if onaddmetric}
            <div class="absolute right-4 top-4 z-10 shadow-lg">
                <button
                    type="button"
                    class="flex items-center gap-2 rounded-lg bg-[#0f172a] px-4 py-2 font-medium text-white shadow-sm transition-colors hover:bg-slate-800"
                    onclick={onaddmetric}
                    data-testid="metric-canvas-add"
                >
                    <Icon icon="lucide:plus" class="h-4 w-4" />
                    Add metric
                </button>
            </div>
        {/if}

        <div
            class="pointer-events-none absolute bottom-4 left-4 z-10 max-w-xs rounded-lg border border-slate-200 bg-white/90 px-3 py-1.5 text-[11px] leading-relaxed text-slate-500 shadow-sm backdrop-blur-sm"
        >
            Drag from a node's right dot onto another node to record an influence. Select an
            arrow and press Backspace to remove it.
        </div>
    {/if}
</div>
