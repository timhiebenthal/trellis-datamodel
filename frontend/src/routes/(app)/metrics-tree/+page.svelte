<script lang="ts">
    import { getConfigInfo, getMetricTree } from '$lib/api';
    import MetricCanvas from '$lib/components/MetricCanvas.svelte';
    import MetricSidebar from '$lib/components/MetricSidebar.svelte';
    import {
        addBoundMetric,
        addDraftMetric,
        connectInfluence,
        removeInfluence,
        removeMetric,
        type MetricGraphState,
    } from '$lib/utils/metric-edits';
    import { layoutFromMetrics, type MetricLayout } from '$lib/utils/metric-graph';
    import type { MetricCatalogEntry, MetricTreeFile } from '$lib/types';

    type MetricTreeResponse = MetricTreeFile & { catalog: MetricCatalogEntry[] };

    let loading = $state(true);
    let metricsEnabled = $state(false);
    let error = $state<string | null>(null);
    let tree = $state<MetricTreeResponse | null>(null);
    let layout = $state<MetricLayout>({});
    let notice = $state<string | null>(null);

    // Detail panel seam (Task 9). Selecting a metric - by clicking its node, its
    // sidebar row, or by creating one - records the id here, and `detailFocus`
    // says which field the panel should focus first. `MetricDetailPanel` reads
    // both when it lands.
    let selectedMetricId = $state<string | null>(null);
    let detailFocus = $state<'label' | null>(null);

    let noticeTimer: ReturnType<typeof setTimeout> | undefined;

    // Check the feature flag, then load the document. Redirect to the canvas
    // when the feature is off, matching the bus-matrix route.
    (async () => {
        try {
            const info = await getConfigInfo();
            metricsEnabled = info?.metrics_enabled ?? false;

            if (!metricsEnabled) {
                window.location.href = '/canvas';
                return;
            }

            tree = await getMetricTree();
            layout = layoutFromMetrics(tree.metrics);
        } catch (e) {
            console.error('Failed to load metric tree:', e);
            error = e instanceof Error ? e.message : 'Failed to load metric tree';
        } finally {
            loading = false;
        }
    })();

    /**
     * Every graph edit is a pure function over `{ metrics, influences }`; this is
     * the single place the page swaps in the result.
     */
    function applyGraph(next: MetricGraphState) {
        if (!tree) return;
        tree = { ...tree, metrics: next.metrics, influences: next.influences };
    }

    /** Explain a refused edit instead of dropping it silently. */
    function flash(message: string) {
        notice = message;
        clearTimeout(noticeTimer);
        noticeTimer = setTimeout(() => (notice = null), 5000);
    }

    function handleAddMetric() {
        if (!tree) return;

        const { state: next, metric } = addDraftMetric(tree);
        applyGraph(next);

        selectedMetricId = metric.id;
        detailFocus = 'label';
    }

    function handleAddCatalogMetric(entry: MetricCatalogEntry) {
        if (!tree) return;

        const outcome = addBoundMetric(tree, entry);
        applyGraph(outcome.state);

        if (!outcome.metric) {
            flash(
                outcome.reason === 'duplicate'
                    ? `${entry.name} is already on the tree.`
                    : `${entry.name} cannot be added: ${entry.reason ?? 'it has no dataset to bind to'}.`,
            );
            return;
        }

        selectedMetricId = outcome.metric.id;
    }

    function handleConnect(driver: string, effect: string) {
        if (!tree) return;

        const outcome = connectInfluence(tree, driver, effect);
        applyGraph(outcome.state);

        if (outcome.ok) {
            notice = null;
            return;
        }

        if (outcome.reason === 'self') {
            flash('A metric cannot influence itself.');
        } else if (outcome.reason === 'duplicate') {
            flash('That influence is already on the tree.');
        }
    }

    function handleDeleteInfluence(driver: string, effect: string) {
        if (!tree) return;
        applyGraph(removeInfluence(tree, driver, effect));
    }

    function handleDeleteMetric(metricId: string) {
        if (!tree) return;

        applyGraph(removeMetric(tree, metricId));

        if (selectedMetricId === metricId) {
            selectedMetricId = null;
            detailFocus = null;
        }
    }

    function handleSelectMetric(metricId: string | null) {
        selectedMetricId = metricId;
        if (!metricId) detailFocus = null;
    }
</script>

<svelte:head>
    <title>trellis - Metric Tree</title>
    <meta name="description" content="Metric tree view - how metrics influence each other" />
</svelte:head>

{#if loading}
    <div class="flex-1 h-full relative w-full flex items-center justify-center">
        <div class="text-center">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-4"></div>
            <p class="text-sm text-gray-600">Loading metric tree...</p>
        </div>
    </div>
{:else if error}
    <div class="flex items-center justify-center h-full">
        <div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg max-w-md">
            <p class="font-medium">Failed to load metric tree</p>
            <p class="text-sm mt-1">{error}</p>
        </div>
    </div>
{:else if metricsEnabled && tree}
    <div class="flex h-full w-full flex-1 overflow-hidden">
        <div class="flex min-w-0 flex-1 flex-col">
            <header class="flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-2.5">
                <div class="min-w-0">
                    <h2 class="text-sm font-semibold text-slate-800">Metric Tree</h2>
                    <!-- Direction is the whole point of this canvas: arrows leave drivers and land on effects. -->
                    <p class="truncate text-xs text-slate-500">
                        Arrows run from a driver to the metric it moves.
                    </p>
                </div>
                <p class="shrink-0 text-xs tabular-nums text-slate-500" data-testid="metric-count">
                    {tree.metrics.length} metrics &middot; {tree.influences.length} influences
                </p>
            </header>

            {#if notice}
                <div
                    class="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-5 py-1.5 text-xs text-amber-800"
                    role="status"
                    data-testid="metric-notice"
                >
                    <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"></span>
                    <span class="min-w-0 flex-1 truncate">{notice}</span>
                    <button
                        type="button"
                        class="shrink-0 rounded p-0.5 text-amber-600 hover:bg-amber-100"
                        aria-label="Dismiss message"
                        onclick={() => (notice = null)}
                    >
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
            {/if}

            <MetricCanvas
                metrics={tree.metrics}
                influences={tree.influences}
                {layout}
                {selectedMetricId}
                onaddmetric={handleAddMetric}
                onselectmetric={handleSelectMetric}
                onconnect={handleConnect}
                ondeleteedge={handleDeleteInfluence}
                ondeletemetric={handleDeleteMetric}
            />
        </div>

        <!-- Task 9 mounts MetricDetailPanel in a rail beside this sidebar, driven by
             selectedMetricId + detailFocus. -->
        <MetricSidebar
            metrics={tree.metrics}
            catalog={tree.catalog}
            {selectedMetricId}
            onaddmetric={handleAddMetric}
            onaddcatalogmetric={handleAddCatalogMetric}
            onselectmetric={handleSelectMetric}
            ondeletemetric={handleDeleteMetric}
        />
    </div>
{:else}
    <div class="flex items-center justify-center h-full text-gray-500">
        <p>Metric tree is not available.</p>
    </div>
{/if}
