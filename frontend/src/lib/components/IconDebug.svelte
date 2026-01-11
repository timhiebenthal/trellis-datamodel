<script lang="ts">
    import Icon from "@iconify/svelte";
    import { onDestroy, onMount } from "svelte";
    import { tick } from "svelte";

    let { icon = "", ...rest } = $props<{ icon: string; [key: string]: any }>();

    // #region agent log
    const iconId = `Icon-${icon}-${Math.random().toString(36).substr(2, 9)}`;
    let mountTimestamp = Date.now();
    console.log(`[${iconId}] MOUNT: ${icon} at ${mountTimestamp}`);
    
    let isDestroyed = false;
    let isReady = false;
    
    onMount(async () => {
        await tick(); // Wait for DOM to be ready
        isReady = true;
        console.log(`[${iconId}] READY: ${icon}`);
    });
    
    onDestroy(async () => {
        if (isDestroyed) {
            console.warn(`[${iconId}] Already destroyed, skipping`);
            return;
        }
        isDestroyed = true;
        const destroyTimestamp = Date.now();
        console.log(`[${iconId}] DESTROY: ${icon} after ${destroyTimestamp - mountTimestamp}ms, isReady=${isReady}`);
        try {
            await tick(); // Try to let Icon component finish cleanup
            fetch('http://127.0.0.1:7242/ingest/5005a234-c969-4c96-a71f-2c33a7d43099',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'IconDebug.svelte:35',message:'Icon onDestroy START',data:{icon,iconId,lifespan:destroyTimestamp - mountTimestamp,isReady,timestamp:Date.now()},timestamp:Date.now(),sessionId:'debug-session',runId:'run4',hypothesisId:'J'})}).catch(()=>{});
        } catch (e) {
            console.error('IconDebug onDestroy error:', e);
        }
    });
    // #endregion
</script>

<svelte:component>
    {#if isReady}
        <Icon {icon} {...rest} />
    {/if}
</svelte:component>
