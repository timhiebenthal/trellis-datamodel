<script lang="ts">
    import {
        SvelteFlow,
        Controls,
        Background,
        BackgroundVariant,
        type Connection,
        type Edge,
        type Node,
    } from "@xyflow/svelte";
    import { setContext } from "svelte";
    import Icon from "$lib/components/Icon.svelte";
    import MetricNode from "./MetricNode.svelte";
    import MetricInfluenceEdge from "./MetricInfluenceEdge.svelte";
    import type { MetricCatalogEntry, MetricEntry, MetricInfluence } from "$lib/types";
    import {
        METRIC_GRID,
        buildMetricEdges,
        buildMetricNodes,
        withMetricPosition,
        type MetricCanvasActions,
        type MetricLayout,
        type MetricRelationKind,
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
        catalog = [],
        layout = {},
        selectedMetricId = null,
        onaddmetric,
        onselectmetric,
        onconnect,
        ondeleteedge,
        ondeletemetric,
        onmove,
        onaddrelateddraft,
        onaddrelatedcatalog,
    }: {
        metrics?: MetricEntry[];
        influences?: MetricInfluence[];
        catalog?: MetricCatalogEntry[];
        layout?: MetricLayout;
        selectedMetricId?: string | null;
        onaddmetric?: () => void;
        onselectmetric?: (metricId: string | null) => void;
        /** Callback receives (driver, effect). In top-to-bottom layout, source is effect (top) and target is driver (bottom). */
        onconnect?: (driver: string, effect: string) => void;
        ondeleteedge?: (driver: string, effect: string) => void;
        ondeletemetric?: (metricId: string) => void;
        /** A node was dropped: the page records its new position. */
        onmove?: (metricId: string, position: { x: number; y: number }) => void;
        /** Create a draft metric above (`effect`) or below (`driver`) `anchorMetricId` and connect it. */
        onaddrelateddraft?: (anchorMetricId: string, relation: MetricRelationKind) => void;
        /** Bind a catalog metric above (`effect`) or below (`driver`) `anchorMetricId` and connect it. */
        onaddrelatedcatalog?: (
            anchorMetricId: string,
            relation: MetricRelationKind,
            entry: MetricCatalogEntry,
        ) => void;
    } = $props();

    const nodeTypes = { metric: MetricNode };
    const edgeTypes = { influence: MetricInfluenceEdge };

    // Node-level actions travel through context so `MetricNodeData` stays the
    // wire shape it is on the server.
    setContext<MetricCanvasActions>("metricCanvas", {
        deleteMetric: (metricId: string) => ondeletemetric?.(metricId),
        getMetrics: () => metrics,
        getCatalog: () => catalog,
        getInfluences: () => influences,
        addRelatedDraft: (anchorMetricId, relation) =>
            onaddrelateddraft?.(anchorMetricId, relation),
        addRelatedCatalogMetric: (anchorMetricId, relation, entry) =>
            onaddrelatedcatalog?.(anchorMetricId, relation, entry),
        connectRelatedMetric: (anchorMetricId, relation, targetMetricId) => {
            if (relation === "driver") {
                onconnect?.(targetMetricId, anchorMetricId);
            } else {
                onconnect?.(anchorMetricId, targetMetricId);
            }
        },
    });

    let dragOverride = $state<{ id: string; position: { x: number; y: number } } | null>(null);

    const effectiveLayout = $derived(
        dragOverride
            ? withMetricPosition(
                  layout,
                  dragOverride.id,
                  dragOverride.position,
                  metrics,
                  influences,
              )
            : layout,
    );

    const flowNodes = $derived(
        buildMetricNodes(
            metrics,
            effectiveLayout,
            selectedMetricId,
            influences,
        ) as unknown as Node[],
    );

    const flowEdges = $derived(
        buildMetricEdges(metrics, influences) as unknown as Edge[],
    );

    const isEmpty = $derived(metrics.length === 0);

    function handleConnect(connection: Connection) {
        if (!connection.source || !connection.target) return;
        // Top-to-bottom tree: source (bottom handle of upper node) is the effect,
        // target (top handle of lower node) is the driver.
        onconnect?.(connection.target, connection.source);
    }

    function handleDelete({ nodes: goneNodes, edges: goneEdges }: { nodes: Node[]; edges: Edge[] }) {
        for (const edge of goneEdges ?? []) {
            ondeleteedge?.(edge.target, edge.source);
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

    function handleNodeDrag({ targetNode }: { targetNode: Node | null }) {
        if (!targetNode) return;
        dragOverride = {
            id: targetNode.id,
            position: { x: targetNode.position.x, y: targetNode.position.y },
        };
    }

    /**
     * Report where a node was dropped. The canvas does not keep that position
     * itself: the page owns the layout, so the save payload and the rendered
     * position can never disagree.
     */
    function handleNodeDragStop({ targetNode }: { targetNode: Node | null }) {
        dragOverride = null;
        if (!targetNode || !onmove) return;
        const aligned = withMetricPosition(
            layout,
            targetNode.id,
            targetNode.position,
            metrics,
            influences,
        )[targetNode.id];
        onmove(targetNode.id, aligned ?? { x: targetNode.position.x, y: targetNode.position.y });
    }

    /** A metric cannot drive itself, and the same connection only exists once. */
    function isValidConnection(connection: Connection | Edge): boolean {
        if (!connection.source || !connection.target) return false;
        if (connection.source === connection.target) return false;

        return !influences.some(
            (influence) =>
                influence.effect === connection.source &&
                influence.drivers.includes(connection.target as string),
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
            snapGrid={[METRIC_GRID.snapX, METRIC_GRID.snapX]}
            fitView
            fitViewOptions={{ padding: 0.3, maxZoom: 1 }}
            panOnDrag
            selectionOnDrag={false}
            onlyRenderVisibleElements
            onconnect={handleConnect}
            ondelete={handleDelete}
            onnodeclick={handleNodeClick}
            onpaneclick={handlePaneClick}
            onnodedrag={handleNodeDrag}
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
            Hover a metric to click <strong>+ Add effect</strong> (top) or
            <strong>+ Add driver</strong> (bottom), or drag a metric from the sidebar onto those buttons.
        </div>
    {/if}
</div>
