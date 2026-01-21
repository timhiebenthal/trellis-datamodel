<script lang="ts">
    import { getContext } from 'svelte';
    import { readable, type Readable } from 'svelte/store';
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
