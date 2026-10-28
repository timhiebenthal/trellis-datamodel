<script lang="ts">
    import { onMount } from 'svelte';
    import { getConfigInfo, getMetricTree } from '$lib/api';
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
        alignMetricLayout,
        buildMetricTreePayload,
        layoutFromMetrics,
        relatedMetricPosition,
        withMetricPosition,
        type MetricLayout,
        type MetricRelationKind,
    } from '$lib/utils/metric-graph';
    import type {
        MetricCatalogEntry,
        MetricEntry,
        MetricTreeFile,
        MetricTreeResponse,
    } from '$lib/types';

    let loading = $state(true);
    let metricsEnabled = $state(false);
    let error = $state<string | null>(null);
    let tree = $state<MetricTreeResponse | null>(null);
    let layout = $state<MetricLayout>({});
    let notice = $state<string | null>(null);

    // Selection drives the detail panel: which metric is open, and which field it
    // should focus when the panel was opened by creating something.
    let selectedMetricId = $state<string | null>(null);
    let detailFocus = $state<'label' | null>(null);

    // "Add metric" opens a draft that is not on the tree. Nothing reaches the
    // document (or the file) until Create, so cancelling leaves no half-defined
    // metric behind. `link` is the metric it will be wired to once created.
    type PendingDraft = {
        draft: MetricEntry;
        link: { anchorMetricId: string; relation: MetricRelationKind } | null;
    };
    let pending = $state<PendingDraft | null>(null);

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

    /** Select a metric (or nothing). Anything else on the page discards an unfinished draft. */
    function select(metricId: string | null, focus: 'label' | null = null) {
        pending = null;
        selectedMetricId = metricId;
        detailFocus = focus;
    }

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

            const document = await getMetricTree();

            tree = document;
            layout = layoutFromMetrics(document.metrics);

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

    function startDraft(link: PendingDraft['link'] = null) {
        if (!tree) return;

        select(null, 'label');
        pending = { draft: { id: 'new-metric', label: '', description: '', expression: '' }, link };
    }

    function handleAddMetric() {
        startDraft();
    }

    function handleCancelDraft() {
        select(null);
    }

    /** Put the finished draft on the tree, wired to its anchor when it came from one. */
    function handleCreateMetric() {
        if (!tree || !pending) return;

        const { draft, link } = pending;
        const { state: withDraft, metric } = addDraftMetric(tree, draft.label);
        const filled = updateMetric(withDraft, metric.id, {
            description: draft.description,
            expression: draft.expression,
            dataset_ref: draft.dataset_ref,
        });

        if (link) {
            const pos = relatedMetricPosition(
                link.anchorMetricId,
                link.relation,
                tree.metrics,
                tree.influences,
                layout,
            );
            const driver = link.relation === 'driver' ? metric.id : link.anchorMetricId;
            const effect = link.relation === 'driver' ? link.anchorMetricId : metric.id;
            const connected = connectInfluence(filled, driver, effect);

            layout = alignMetricLayout(
                connected.state.metrics,
                connected.state.influences,
                withMetricPosition(layout, metric.id, pos),
            );
            applyGraph(connected.state);
        } else {
            applyGraph(filled);
        }

        select(metric.id);
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

        select(outcome.metric.id);
    }

    function handleAddRelatedDraft(anchorMetricId: string, relation: MetricRelationKind) {
        startDraft({ anchorMetricId, relation });
    }

    function handleAddRelatedCatalogMetric(
        anchorMetricId: string,
        relation: MetricRelationKind,
        entry: MetricCatalogEntry,
    ) {
        if (!tree) return;

        const pos = relatedMetricPosition(
            anchorMetricId,
            relation,
            tree.metrics,
            tree.influences,
            layout,
        );

        // If the catalog entry is already on the tree, connect the existing metric.
        const existing = tree.metrics.find(
            (metric) =>
                metric.binding?.name === entry.name &&
                (!entry.dataset || metric.binding?.dataset === entry.dataset),
        );
        if (existing) {
            const driver = relation === 'driver' ? existing.id : anchorMetricId;
            const effect = relation === 'driver' ? anchorMetricId : existing.id;
            handleConnect(driver, effect);
            return;
        }

        const added = addBoundMetric(tree, entry);
        if (!added.metric) {
            flash(
                `${entry.name} cannot be added: ${entry.reason ?? 'it has no dataset to bind to'}.`,
            );
            return;
        }

        const driver = relation === 'driver' ? added.metric.id : anchorMetricId;
        const effect = relation === 'driver' ? anchorMetricId : added.metric.id;
        const connected = connectInfluence(added.state, driver, effect);

        layout = alignMetricLayout(
            connected.state.metrics,
            connected.state.influences,
            withMetricPosition(layout, added.metric.id, pos),
        );
        applyGraph(connected.state);

        select(added.metric.id);
    }

    function handleConnect(driver: string, effect: string) {
        if (!tree) return;

        const outcome = connectInfluence(tree, driver, effect);
        if (outcome.ok) {
            layout = alignMetricLayout(outcome.state.metrics, outcome.state.influences, layout);
        }
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
        const next = removeInfluence(tree, driver, effect);
        layout = alignMetricLayout(next.metrics, next.influences, layout);
        applyGraph(next);
    }

    function handleDeleteMetric(metricId: string) {
        if (!tree) return;

        const next = removeMetric(tree, metricId);
        layout = alignMetricLayout(next.metrics, next.influences, layout);
        applyGraph(next);

        if (selectedMetricId === metricId) select(null);
        else pending = null;
    }

    function handleSelectMetric(metricId: string | null) {
        // A deliberate selection is not a "start typing" moment.
        select(metricId);
    }

    /**
     * A dropped node updates the local runtime layout on the canvas without
     * rewriting `metric_tree.yml`.
     */
    function handleMoveMetric(metricId: string, position: { x: number; y: number }) {
        layout = withMetricPosition(
            layout,
            metricId,
            position,
            tree?.metrics ?? [],
            tree?.influences ?? [],
        );
    }

    function handleMetricChange(patch: Partial<MetricEntry>) {
        if (pending) {
            pending = { ...pending, draft: { ...pending.draft, ...patch } };
            return;
        }
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
                    <p class="truncate text-xs text-slate-500">
                        Top-down hierarchy from high-level metrics to the input metrics that drive them.
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
                    catalog={tree.catalog}
                    {layout}
                    {selectedMetricId}
                    onaddmetric={handleAddMetric}
                    onselectmetric={handleSelectMetric}
                    onconnect={handleConnect}
                    ondeleteedge={handleDeleteInfluence}
                    ondeletemetric={handleDeleteMetric}
                    onmove={handleMoveMetric}
                    onaddrelateddraft={handleAddRelatedDraft}
                    onaddrelatedcatalog={handleAddRelatedCatalogMetric}
                />

                <!-- Inspector overlays the canvas instead of shrinking it, so opening a
                     metric never moves the graph under the cursor. It starts below the
                     canvas's own "Add metric" button and only exists while something is
                     selected, so an idle canvas stays unobstructed. -->
                {#if pending || selectedMetric}
                    <div class="absolute bottom-4 right-4 top-16 z-20 flex">
                        <MetricDetailPanel
                            metric={pending ? pending.draft : selectedMetric}
                            isNew={pending !== null}
                            oncreate={handleCreateMetric}
                            oncancel={handleCancelDraft}
                            datasets={tree.datasets}
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
