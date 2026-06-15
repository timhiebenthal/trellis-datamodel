<script lang="ts">
    import { getContext } from 'svelte';
    import { readable, type Readable } from 'svelte/store';
    import { page } from '$app/stores';
    import { viewMode, nodes, edges, sidebarSearchTerm } from '$lib/stores';
    import Canvas from '$lib/components/Canvas.svelte';
    import type { GuidanceConfig } from '$lib/types';

    const loadingStore =
        getContext<Readable<boolean>>('loading') ?? readable(false);
    const loading = $derived($loadingStore);

    const guidanceConfigStore =
        getContext<Readable<GuidanceConfig>>('guidanceConfig') ??
        readable({
            entity_wizard_enabled: true,
            push_warning_enabled: true,
            min_description_length: 10,
            disabled_guidance: [],
        });
    const guidanceConfig = $derived($guidanceConfigStore);

    const lineageEnabledStore =
        getContext<Readable<boolean>>('lineageEnabled') ?? readable(false);
    const lineageEnabled = $derived($lineageEnabledStore);

    const exposuresEnabledStore =
        getContext<Readable<boolean>>('exposuresEnabled') ?? readable(false);
    const exposuresEnabled = $derived($exposuresEnabledStore);

    const hasExposuresDataStore =
        getContext<Readable<boolean>>('hasExposuresData') ?? readable(false);
    const hasExposuresData = $derived($hasExposuresDataStore);

    // Read URL parameters for entity filtering
    const entitiesParam = $derived($page.url.searchParams.get('entities'));
    const eventTextParam = $derived($page.url.searchParams.get('eventText'));

    // Parse comma-separated entity IDs from URL parameter, or filter by sidebar search term
    const filteredEntityIds = $derived(
        entitiesParam
            ? entitiesParam.split(',').filter(id => id.trim())
            : $sidebarSearchTerm.trim()
                ? $nodes
                    .filter(n => n.type === 'entity' && (n.data as any)?.label?.toLowerCase().includes($sidebarSearchTerm.trim().toLowerCase()))
                    .map(n => n.id)
                : null
    );

    // Pass event text for banner display
    const filterEventText = $derived(eventTextParam || null);

</script>

<svelte:head>
    <title>trellis - Canvas</title>
    <meta name="description" content="Visual data modeling canvas - design and document your data models" />
</svelte:head>

{#if loading}
    <div class="flex-1 h-full relative w-full flex items-center justify-center">
        <div class="text-center">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-4"></div>
            <p class="text-sm text-gray-600">Loading data model...</p>
        </div>
    </div>
{:else}
    <div class="flex-1 h-full relative w-full" data-testid="canvas-ready">
        <Canvas
            guidanceConfig={guidanceConfig}
            lineageEnabled={lineageEnabled}
            exposuresEnabled={exposuresEnabled}
            hasExposuresData={hasExposuresData}
            filteredEntityIds={filteredEntityIds}
            filterEventText={filterEventText}
        />
    </div>
{/if}
