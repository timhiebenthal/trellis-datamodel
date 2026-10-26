<script lang="ts">
    import {
        SvelteFlow,
        Controls,
        Background,
        BackgroundVariant,
        MarkerType,
        type Edge,
        type Node,
    } from "@xyflow/svelte";
    import Icon from "$lib/components/Icon.svelte";
    import MetricNode from "./MetricNode.svelte";
    import MetricInfluenceEdge from "./MetricInfluenceEdge.svelte";
    import type { MetricEntry, MetricInfluence } from "$lib/types";
    import {
        METRIC_ACCENT,
        buildMetricEdges,
        buildMetricNodes,
        type MetricLayout,
    } from "$lib/utils/metric-graph";

    /**
     * The metric canvas. It is deliberately not `Canvas.svelte`: no groups, no
     * filters, no lineage, no star-schema positioner, and no reads of the global
     * `nodes`/`edges` stores. Everything it draws comes from the props below.
     */
    let {
        metrics = [],
        influences = [],
        layout = {},
        onaddmetric,
    }: {
        metrics?: MetricEntry[];
        influences?: MetricInfluence[];
        layout?: MetricLayout;
        onaddmetric?: () => void;
    } = $props();

    const nodeTypes = { metric: MetricNode };
    const edgeTypes = { influence: MetricInfluenceEdge };

    const flowNodes = $derived(buildMetricNodes(metrics, layout) as unknown as Node[]);

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
    {/if}
</div>
