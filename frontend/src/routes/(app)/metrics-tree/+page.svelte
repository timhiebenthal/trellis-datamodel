<script lang="ts">
    import { onMount } from 'svelte';
    import { getConfigInfo, getDataModel, getMetricTree } from '$lib/api';
    import MetricCanvas from '$lib/components/MetricCanvas.svelte';
    import MetricDetailPanel from '$lib/components/MetricDetailPanel.svelte';
    import MetricSidebar from '$lib/components/MetricSidebar.svelte';
    import { MetricTreeSaveService, type MetricTreeSaveState } from '$lib/services/metric-tree-save';
    import {
        addBoundMetric,
        addDraftMetric,
        connectInfluence,
        incompleteDraftIds,
        removeInfluence,
        removeMetric,
        unlinkMetric,
        updateMetric,
        type MetricGraphState,
    } from '$lib/utils/metric-edits';
    import {
        buildMetricTreePayload,
        layoutFromMetrics,
        withMetricPosition,
        type MetricLayout,
    } from '$lib/utils/metric-graph';
    import type { MetricCatalogEntry, MetricEntry, MetricTreeFile } from '$lib/types';

    type MetricTreeResponse = MetricTreeFile & { catalog: MetricCatalogEntry[] };

    let loading = $state(true);
    let metricsEnabled = $state(false);
    let error = $state<string | null>(null);
    let tree = $state<MetricTreeResponse | null>(null);
    let layout = $state<MetricLayout>({});
    let entityIds = $state<string[]>([]);
    let notice = $state<string | null>(null);

    // Selection drives the detail panel: which metric is open, and which field it
    // should focus when the panel was opened by creating something.
    let selectedMetricId = $state<string | null>(null);
    let detailFocus = $state<'label' | null>(null);

    let saveState = $state<MetricTreeSaveState>({ isSaving: false, warnings: [], error: null });
    let hasUnsavedChanges = $state(false);
    let baselineReady = false;

    let noticeTimer: ReturnType<typeof setTimeout> | undefined;

    const saver = new MetricTreeSaveService({
        debounceMs: 400,
        // The backend rejects a draft without an expression with 422, so autosave
        // waits for a complete document instead of posting a doomed payload.
        canSave: (payload) => incompleteDraftIds(payload.metrics).length === 0,
        onStateChange: (state) => {
            saveState = state;
            hasUnsavedChanges = currentPayload() ? saver.hasUnsavedChanges(currentPayload()!) : false;
        },
    });

    const selectedMetric = $derived(
        tree?.metrics.find((metric) => metric.id === selectedMetricId) ?? null,
    );
    const incompleteIds = $derived(incompleteDraftIds(tree?.metrics ?? []));

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

            const [document, dataModel] = await Promise.all([
                getMetricTree(),
                // Only used to suggest entity ids for `dataset_ref`; a failure here
                // must not block the canvas.
                getDataModel().catch(() => null),
            ]);

            tree = document;
            layout = layoutFromMetrics(document.metrics);
            entityIds = (dataModel?.entities ?? []).map((entity) => entity.id);

            // The freshly loaded document counts as saved: loading must never post.
            saver.initializeBaseline(buildMetricTreePayload(tree, layout));
            baselineReady = true;
        } catch (e) {
            console.error('Failed to load metric tree:', e);
            error = e instanceof Error ? e.message : 'Failed to load metric tree';
        } finally {
            loading = false;
        }
    })();

    onMount(() => {
        // The debounce would otherwise drop the last edit when the tab closes.
        const handleBeforeUnload = () => {
            if (!tree) return;
            void saver.flushSync(buildMetricTreePayload(tree, layout));
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    });

    /**
     * The POST body for the current document, positions included. `null` until the
     * document has loaded.
     */
    function currentPayload(): MetricTreeFile | null {
        if (!tree) return null;
        return buildMetricTreePayload(tree, layout);
    }

    /**
     * Ask for a debounced save. Called from `applyGraph` and from layout changes -
     * deliberately not from an effect: the service reports progress synchronously,
     * and writing page state from inside an effect that also reads the document
     * makes Svelte's scheduler loop.
     */
    function requestSave() {
        const payload = currentPayload();
        if (!baselineReady || !payload) return;
        saver.save(payload);
    }

    function applyGraph(next: MetricGraphState) {
        if (!tree) return;
        tree = { ...tree, metrics: next.metrics, influences: next.influences };
        requestSave();
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
        detailFocus = null;
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
        // A deliberate selection is not a "start typing" moment.
        detailFocus = null;
    }

    /**
     * A dropped node updates the local layout first and the save follows, so the
     * position is in the very next payload rather than a reload later.
     */
    function handleMoveMetric(metricId: string, position: { x: number; y: number }) {
        layout = withMetricPosition(layout, metricId, position);
        requestSave();
    }

    function handleMetricChange(patch: Partial<MetricEntry>) {
        if (!tree || !selectedMetricId) return;
        applyGraph(updateMetric(tree, selectedMetricId, patch));
    }

    function handleUnlinkMetric(metricId: string) {
        if (!tree) return;

        applyGraph(unlinkMetric(tree, metricId));
        flash('Unlinked. Write an expression so this metric can be saved as a draft.');
        detailFocus = 'label';
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
        <MetricSidebar
            metrics={tree.metrics}
            catalog={tree.catalog}
            {selectedMetricId}
            onaddmetric={handleAddMetric}
            onaddcatalogmetric={handleAddCatalogMetric}
            onselectmetric={handleSelectMetric}
            ondeletemetric={handleDeleteMetric}
        />

        <div class="relative flex min-w-0 flex-1 flex-col">
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

            <div class="relative min-h-0 flex-1">
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
                    onmove={handleMoveMetric}
                />

                <!-- Inspector overlays the canvas instead of shrinking it, so opening a
                     metric never moves the graph under the cursor. It starts below the
                     canvas's own "Add metric" button and only exists while something is
                     selected, so an idle canvas stays unobstructed. -->
                {#if selectedMetric}
                    <div class="absolute bottom-4 right-4 top-16 z-20 flex">
                        <MetricDetailPanel
                            metric={selectedMetric}
                            {entityIds}
                            focus={detailFocus}
                            warnings={saveState.warnings}
                            error={saveState.error}
                            isSaving={saveState.isSaving}
                            {hasUnsavedChanges}
                            {incompleteIds}
                            onchange={handleMetricChange}
                            onunlink={handleUnlinkMetric}
                            onclose={() => handleSelectMetric(null)}
                        />
                    </div>
                {/if}
            </div>
        </div>
    </div>
{:else}
    <div class="flex items-center justify-center h-full text-gray-500">
        <p>Metric tree is not available.</p>
    </div>
{/if}
