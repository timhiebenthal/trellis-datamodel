<script lang="ts">
    import { viewMode, configStatus } from '$lib/stores';
    import { getConfigStatus, getConfigInfo, getExposures } from '$lib/api';
    import ExposuresTable from '$lib/components/ExposuresTable.svelte';

    let loading = $state(true);
    let exposuresEnabled = $state(false);
    let exposuresDefaultLayout = $state<'dashboards-as-rows' | 'entities-as-rows'>('dashboards-as-rows');
    let hasExposuresData = $state(false);

    // Set view mode and check exposures availability on mount
    (async () => {
        try {
            const status = await getConfigStatus();
            $configStatus = status;
            
            const info = await getConfigInfo();
            exposuresEnabled = info?.exposures_enabled ?? false;
            exposuresDefaultLayout = info?.exposures_default_layout ?? 'dashboards-as-rows';
            
            if (exposuresEnabled) {
                const exposuresData = await getExposures();
                hasExposuresData = exposuresData.exposures.length > 0;
            }

            if (exposuresEnabled && hasExposuresData) {
                $viewMode = 'exposures';
            } else {
                // Redirect to canvas if exposures not available
                window.location.href = '/canvas';
            }
        } catch (e) {
            console.error('Failed to load exposures:', e);
            window.location.href = '/canvas';
        } finally {
            loading = false;
        }
    })();
</script>

<svelte:head>
    <title>trellis - Exposures</title>
    <meta name="description" content="Exposures view - visualize your dbt exposures and downstream data products" />
</svelte:head>

{#if !loading && exposuresEnabled && hasExposuresData}
    <ExposuresTable {exposuresEnabled} {exposuresDefaultLayout} />
{:else if !loading}
    <div class="flex items-center justify-center h-full text-gray-500">
        <p>Exposures view is not available.</p>
    </div>
{/if}
