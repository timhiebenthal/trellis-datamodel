<script lang="ts">
    import Icon from "@iconify/svelte";
    import { onDestroy, onMount } from "svelte";
    import { tick } from "svelte";

    let { icon = "", ...rest } = $props<{ icon: string; [key: string]: any }>();

    let isDestroyed = $state(false);
    let isReady = $state(false);
    
    onMount(async () => {
        await tick(); // Wait for DOM to be ready
        isReady = true;
    });
    
    onDestroy(() => {
        if (isDestroyed) {
            return;
        }
        isDestroyed = true;
    });
</script>

{#if isReady}
    <Icon {icon} {...rest} />
{/if}
