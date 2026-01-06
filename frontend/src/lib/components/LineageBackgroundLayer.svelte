<script lang="ts">
    import type { LineageNode } from "$lib/types";

    const { bands = [], viewport = { x: 0, y: 0, zoom: 1 } } = $props<{
        bands: Array<{
            id: string;
            x: number;
            y: number;
            width: number;
            height: number;
            label: string;
            isUnassigned: boolean;
        }>;
        viewport: { x: number; y: number; zoom: number };
    }>();

    $effect(() => {
        void bands;
        void viewport;
    });
</script>

<div class="absolute inset-0 overflow-hidden pointer-events-none z-0">
    <!-- Bands are now in screen coordinates, so no viewport transform needed -->
    <div class="absolute top-0 left-0 w-full h-full">
        {#each bands as band (band.id)}
            <!-- Normal band with subtle styling -->
            <div
                class={`absolute border-y shadow-[inset_0_1px_0_0_rgba(255,255,255,0.4)] ${
                    band.isUnassigned
                        ? "border-gray-300/30 bg-gray-200/50"
                        : "border-primary-600/30 bg-primary-500/[0.20]"
                }`}
                style={`
                    /* Bands are in graph coordinates, but we need to adjust for the visible viewport */
                    /* Since viewport is at x=0, we need to shift bands right by 50130px to make them visible */
                    left: ${band.x + 50130}px;
                    top: ${band.y}px;
                    width: ${band.width}px; 
                    height: ${band.height}px;
                `}
            >
                
                <!-- DEBUG: Add subtle visual indicator for debugging -->
                
                <!-- Label area -->
                <div
                    class="pt-4 pl-5 select-none text-[10px] font-bold uppercase tracking-[0.3em] ${band.isUnassigned
                        ? 'text-gray-500/60'
                        : 'text-primary-700/50'}"
                >
                    <span
                        class={band.isUnassigned
                            ? "text-gray-500/60"
                            : "text-primary-700/50"}
                    >
                        {band.label}
                    </span>
                </div>
            </div>
        {/each}
    </div>
    

</div>