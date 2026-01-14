<script lang="ts">
    import { page } from '$app/stores';
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
    const lineageEnabled = true;
    const exposuresEnabled = true;
    const hasExposuresData = false;
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
