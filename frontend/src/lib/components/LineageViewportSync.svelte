<script lang="ts">
    import {
        useNodesInitialized,
        useSvelteFlow,
        useViewportInitialized,
    } from "@xyflow/svelte";

    const {
        bands = [],
        onViewportChange,
        onNodesInitialized,
        onViewportInitialized,
        fitNodeIds = [],
    } = $props<{
        bands: Array<{ id: string; bandX: number }>;
        onViewportChange?: (viewport: {
            x: number;
            y: number;
            zoom: number;
        }) => void;
        onNodesInitialized?: () => void;
        onViewportInitialized?: () => void;
        fitNodeIds?: string[];
    }>();

    const { getViewport, updateNodeData, fitView } = useSvelteFlow();
    const nodesInitialized = useNodesInitialized();
    const viewportInitialized = useViewportInitialized();

    let lastLeftEdge = 0;
    let forceUpdateLabels = false;
    let didNotifyInitialized = false;
    let didNotifyViewportInitialized = false;
    let didFit = false;

    $effect(() => {
        if (didNotifyInitialized) return;
        if (!nodesInitialized.current) return;
        didNotifyInitialized = true;
        onNodesInitialized?.();
    });

    $effect(() => {
        if (didNotifyViewportInitialized) return;
        if (!viewportInitialized.current) return;
        didNotifyViewportInitialized = true;
        onViewportInitialized?.();
    });

    $effect(() => {
        if (didFit) return;
        if (!nodesInitialized.current) return;
        if (!viewportInitialized.current) return;
        if (!fitNodeIds?.length) return;

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                try {
                    fitView({
                        padding: 0.3,
                        nodes: fitNodeIds.map((id: string) => ({ id })),
                        includeHiddenNodes: false,
                        maxZoom: 0.85,
                        minZoom: 0.05,
                    });
                    didFit = true;
                } catch (e) {
                    console.error("fitView error", e);
                }
            });
        });
    });

    function tick() {
        const viewport = getViewport();
        const leftEdgeInGraph = -viewport.x / viewport.zoom;

        if (forceUpdateLabels || Math.abs(leftEdgeInGraph - lastLeftEdge) > 0.25) {
            lastLeftEdge = leftEdgeInGraph;
            forceUpdateLabels = false;

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

    // When bands are recreated (e.g. on progressive expansion), labelX resets.
    // Force one recompute even if viewport didn't change.
    $effect(() => {
        const _ = bands.length;
        forceUpdateLabels = true;
    });
</script>

<!-- This component renders nothing; it only syncs viewport -> band label positions -->
