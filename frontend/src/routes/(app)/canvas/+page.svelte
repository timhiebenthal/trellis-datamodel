<script lang="ts">
    import { getContext } from 'svelte';
    import { readable, type Readable } from 'svelte/store';
    import { viewMode, nodes, edges } from '$lib/stores';
    import Canvas from '$lib/components/Canvas.svelte';
    import type { GuidanceConfig } from '$lib/types';

    // Get shared state from parent layout context
    const guidanceConfig: GuidanceConfig = {
        entity_wizard_enabled: true,
        push_warning_enabled: true,
        min_description_length: 10,
        disabled_guidance: [],
    };

    // These are set by the parent layout
    const lineageEnabledStore =
        getContext<Readable<boolean>>('lineageEnabled') ?? readable(false);
    const exposuresEnabledStore =
        getContext<Readable<boolean>>('exposuresEnabled') ?? readable(false);
    const hasExposuresDataStore =
        getContext<Readable<boolean>>('hasExposuresData') ?? readable(false);

    const lineageEnabled = $derived($lineageEnabledStore);
    const exposuresEnabled = $derived($exposuresEnabledStore);
    const hasExposuresData = $derived($hasExposuresDataStore);

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
/>
