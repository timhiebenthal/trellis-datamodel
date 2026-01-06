<script lang="ts">
    import { useSvelteFlow } from "@xyflow/svelte";

    const { bands = [], onViewportChange } = $props<{
        bands: Array<{ id: string; bandX: number }>;
        onViewportChange?: (viewport: {
            x: number;
            y: number;
            zoom: number;
        }) => void;
    }>();

    const { getViewport, updateNodeData } = useSvelteFlow();

    let lastLeftEdge = 0;

    function tick() {
        const viewport = getViewport();
        const leftEdgeInGraph = -viewport.x / viewport.zoom;

        if (Math.abs(leftEdgeInGraph - lastLeftEdge) > 0.25) {
            lastLeftEdge = leftEdgeInGraph;

            for (const band of bands) {
                // labelX is interpreted inside the band as padding from the band's left edge (bandX)
                updateNodeData(band.id, {
                    labelX: leftEdgeInGraph + 20 - band.bandX,
                });
            }
        }

        // Sync external layers every frame
        onViewportChange?.(viewport);
    }

    // Keep labels pinned while panning/zooming (and after fitView)
    $effect(() => {
        let raf = 0;

        const loop = () => {
            tick();
            raf = requestAnimationFrame(loop);
        };

        raf = requestAnimationFrame(loop);

        return () => cancelAnimationFrame(raf);
    });
</script>

<!-- This component renders nothing; it only syncs viewport -> band label positions -->
