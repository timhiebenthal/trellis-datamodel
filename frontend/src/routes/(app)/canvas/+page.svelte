<script lang="ts">
    import { getContext } from 'svelte';
    import { readable, type Readable } from 'svelte/store';
    import { page } from '$app/stores';
    import { viewMode, nodes, edges } from '$lib/stores';
    import Canvas from '$lib/components/Canvas.svelte';
    import type { GuidanceConfig } from '$lib/types';

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

    // Parse comma-separated entity IDs from URL parameter
    const filteredEntityIds = $derived(
        entitiesParam ? entitiesParam.split(',').filter(id => id.trim()) : null
    );

    // Pass event text for banner display
    const filterEventText = $derived(eventTextParam || null);

</script>

<svelte:head>
    <title>trellis - Canvas</title>
    <meta name="description" content="Visual data modeling canvas - design and document your data models" />
</svelte:head>

<Canvas
    guidanceConfig={guidanceConfig}
    lineageEnabled={lineageEnabled}
    exposuresEnabled={exposuresEnabled}
    hasExposuresData={hasExposuresData}
    filteredEntityIds={filteredEntityIds}
    filterEventText={filterEventText}
/>
