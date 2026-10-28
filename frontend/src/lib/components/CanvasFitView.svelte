<script lang="ts">
    import { useSvelteFlow, type Node } from "@xyflow/svelte";
    import { nodes } from "$lib/stores";

    // Fits the viewport once the canvas has settled after boot. Without this,
    // the viewport stays pinned at the world origin: content saved at negative
    // or wide coordinates renders offscreen, and the canvas filter bar covers
    // whatever sits at the origin (e.g. a folder group's header/badge).
    let { active }: { active: boolean } = $props();

    const { fitView } = useSvelteFlow();

    let fitted = false;
    // Flips once the boot fit's animation has finished, so callers (and e2e
    // tests) can tell the viewport is no longer moving under the pointer (#170).
    let fitSettled = $state(false);

    $effect(() => {
        if (!active || fitted) return;

        const entityCount = $nodes.filter((n: Node) => n.type === "entity").length;
        if (entityCount === 0) return;

        // Defer until the nodes are measured, then fit once.
        const timer = setTimeout(() => {
            fitted = true;
            void fitView({ padding: 0.15, maxZoom: 1.2, duration: 250 }).finally(() => {
                fitSettled = true;
            });
        }, 250);
        return () => clearTimeout(timer);
    });
</script>

{#if fitSettled}
    <div data-testid="canvas-fitted" hidden></div>
{/if}
