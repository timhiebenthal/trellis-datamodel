<script lang="ts">
    import { getConfigInfo, getMetricTree } from '$lib/api';
    import type { MetricCatalogEntry, MetricTreeFile } from '$lib/types';

    type MetricTreeResponse = MetricTreeFile & { catalog: MetricCatalogEntry[] };

    let loading = $state(true);
    let metricsEnabled = $state(false);
    let error = $state<string | null>(null);
    let tree = $state<MetricTreeResponse | null>(null);

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
        } catch (e) {
            console.error('Failed to load metric tree:', e);
            error = e instanceof Error ? e.message : 'Failed to load metric tree';
        } finally {
            loading = false;
        }
    })();
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
    <div class="flex-1 h-full relative w-full overflow-auto bg-gray-50 p-6">
        <h2 class="text-lg font-semibold text-gray-900">Metric Tree</h2>
        <p class="mt-1 text-sm text-gray-600" data-testid="metric-count">
            {tree.metrics.length} metrics &middot; {tree.influences.length} influences
        </p>
    </div>
{:else}
    <div class="flex items-center justify-center h-full text-gray-500">
        <p>Metric tree is not available.</p>
    </div>
{/if}
