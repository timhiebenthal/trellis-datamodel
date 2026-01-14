<script lang="ts">
    import { viewMode, configStatus } from '$lib/stores';
    import { getConfigStatus, getConfigInfo } from '$lib/api';
    import BusMatrix from '$lib/components/BusMatrix.svelte';

    let loading = $state(true);
    let busMatrixEnabled = $state(false);

    // Set view mode and check bus matrix availability on mount
    (async () => {
        try {
            const status = await getConfigStatus();
            $configStatus = status;
            
            const info = await getConfigInfo();
            busMatrixEnabled = info?.bus_matrix_enabled ?? false;

            if (busMatrixEnabled) {
                $viewMode = 'bus_matrix';
            } else {
                // Redirect to canvas if bus matrix not available
                window.location.href = '/canvas';
            }
        } catch (e) {
            console.error('Failed to load bus matrix:', e);
            window.location.href = '/canvas';
        } finally {
            loading = false;
        }
    })();
</script>

<svelte:head>
    <title>trellis - Bus Matrix</title>
    <meta name="description" content="Bus matrix view - understand data flow across your data models" />
</svelte:head>

{#if !loading && busMatrixEnabled}
    <BusMatrix />
{:else if !loading}
    <div class="flex items-center justify-center h-full text-gray-500">
        <p>Bus matrix view is not available.</p>
    </div>
{/if}
