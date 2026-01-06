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

    // Debug: Log bands info only once to avoid spam
    let debugLogged = false;
    $effect(() => {
        if (bands.length > 0 && !debugLogged) {
            console.log("✅ LineageBackgroundLayer: Received", bands.length, "bands");
            console.table(bands.map(b => ({id: b.id, label: b.label, x: Math.round(b.x), y: Math.round(b.y), width: Math.round(b.width), height: Math.round(b.height)})));
            console.log("📊 Adjusted positions (screen):", bands.map(b => ({id: b.id, x: Math.round(b.x + 50130), y: Math.round(b.y)})));
            console.log("📊 Viewport:", viewport);
            debugLogged = true;
        } else if (bands.length === 0 && !debugLogged) {
            console.log("⚠️ LineageBackgroundLayer: No bands received");
            debugLogged = true;
        }
    });
</script>

<div class="absolute inset-0 overflow-hidden pointer-events-none z-0">
    <!-- Bands are now in screen coordinates, so no viewport transform needed -->
    <div class="absolute top-0 left-0 w-full h-full">
    
    <!-- Debug: Add a visible reference point at origin -->
    <div
        class="absolute w-4 h-4 bg-red-500 rounded-full"
        style="left: 0; top: 0; transform: translate(-2px, -2px); z-index: 100;"
        title="Screen Origin (0,0)"
    ></div>
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
                    /* Temporary debug: add visible border to confirm positioning */
                    outline: 1px solid rgba(0, 0, 255, 0.3);
                `}
            >
                
                <!-- DEBUG: Add subtle visual indicator for debugging -->
                {#if band.id === bands[0]?.id}
                    <div
                        class="absolute top-2 right-2 bg-primary-600 text-white px-2 py-1 text-xs font-bold rounded"
                        style="pointer-events: none;"
                        title="Debug: Band {band.label}"
                    >
                        DEBUG
                    </div>
                {/if}
                
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