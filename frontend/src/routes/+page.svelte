<script lang="ts">
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';
    import { getConfigInfo } from '$lib/api';

    let loading = true;

    onMount(() => {
        let active = true;

        async function navigateToStartPage() {
            let destination = '/canvas';

            try {
                const config = await getConfigInfo();
                const startPage = (config as { start_page?: unknown } | null | undefined)?.start_page;
                if (startPage === 'entity-list') {
                    destination = '/entity-list';
                } else if (startPage !== 'canvas') {
                    destination = '/canvas';
                }
            } catch {
                destination = '/canvas';
            }

            if (active) {
                loading = false;
                await goto(destination, { replaceState: true });
            }
        }

        void navigateToStartPage();

        return () => {
            active = false;
        };
    });
</script>

<svelte:head>
    <title>trellis</title>
</svelte:head>

<main
    class="flex min-h-screen items-center justify-center bg-gray-50 text-sm text-gray-600"
    aria-busy={loading}
    data-testid="start-page-loading"
>
    Loading...
</main>
