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
</script>

<div class="absolute inset-0 overflow-hidden pointer-events-none z-0">
    <!-- Transform container synced with graph viewport -->
    <div
        class="absolute top-0 left-0 w-full h-full"
        style={`transform-origin: 0 0; transform: translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom});`}
    >
        {#each bands as band (band.id)}
            <div
                class={`absolute border-y shadow-[inset_0_1px_0_0_rgba(255,255,255,0.4)] ${
                    band.isUnassigned
                        ? "border-gray-300 bg-gray-200"
                        : "border-blue-300 bg-blue-100"
                }`}
                style={`
                    left: ${band.x}px;
                    top: ${band.y}px;
                    width: ${band.width}px; 
                    height: ${band.height}px;
                `}
            >
                <!-- Label area (using simplified logic until labelX sync in place for this layer) -->
                <!-- For now, just pin label to left side or use sticky if possible, but sticky inside transform is tricky -->
                <!-- We can just display it at left+20px for start -->
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
