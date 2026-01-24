<script lang="ts">
    import { viewMode, configStatus, modelingStyle } from '$lib/stores';
    import { getConfigStatus, getConfigInfo } from '$lib/api';
    import BusinessEvents from '$lib/components/BusinessEvents.svelte';

    let loading = $state(true);
    let businessEventsEnabled = $state(false);
    let error = $state<string | null>(null);

    // Set view mode and check business events availability on mount
    (async () => {
        try {
            const status = await getConfigStatus();
            $configStatus = status;
            
            const info = await getConfigInfo();
            businessEventsEnabled = info?.business_events_enabled ?? false;
            // Update modeling style from config if available
            if (info?.modeling_style) {
                $modelingStyle = info.modeling_style;
            }
            
            // Check if business events is enabled and modeling style is dimensional_model
            if (businessEventsEnabled && $modelingStyle === 'dimensional_model') {
                $viewMode = 'business_events';
            } else {
                // Redirect to canvas if business events not available
                window.location.href = '/canvas';
            }
        } catch (e) {
            console.error('Failed to load business events:', e);
            error = e instanceof Error ? e.message : 'Failed to load business events configuration';
            // Redirect to canvas on error
            window.location.href = '/canvas';
        } finally {
            loading = false;
        }
    })();
</script>

<svelte:head>
    <title>trellis - Business Events</title>
    <meta name="description" content="Business Events modeling for dimensional data models (BEAM* methodology)" />
</svelte:head>

{#if loading}
    <div class="flex items-center justify-center h-full">
        <div class="flex flex-col items-center gap-3">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p class="text-sm text-gray-600">Loading business events...</p>
        </div>
    </div>
{:else if error}
    <div class="flex items-center justify-center h-full">
        <div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg max-w-md">
            <p class="font-medium">Failed to load business events</p>
            <p class="text-sm mt-1">{error}</p>
        </div>
    </div>
{:else if businessEventsEnabled && $modelingStyle === 'dimensional_model'}
    <BusinessEvents />
{:else}
    <div class="flex items-center justify-center h-full text-gray-500">
        <p>Business Events view is not available.</p>
    </div>
{/if}
