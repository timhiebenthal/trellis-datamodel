<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";
import { onMount } from "svelte";

    let { data, selected }: NodeProps = $props();
    
    const isTarget = $derived((data?.level as number) === 0);
    const label = $derived((data?.label as string) || '');
    const connectedToSelected = $derived((data?._connectedToSelected as boolean) ?? false);
    const isGhosted = $derived((data?._ghosted as boolean) ?? false);
    const hiddenCount = $derived((data?._hiddenCount as number) ?? 0);
    const expandHidden = $derived((data?._expandHidden as (() => void) | undefined));
    const onHoverInSources = $derived((data?._onHoverInSources as (() => void) | undefined));
    const onHoverOutSources = $derived((data?._onHoverOutSources as (() => void) | undefined));

onMount(() => {
});
</script>

<div
    class="relative rounded-lg border-2 shadow-md px-3 py-2 min-w-[120px] max-w-[200px] text-center transition-opacity"
    class:bg-white={!isTarget}
    class:border-gray-300={!isTarget}
    class:bg-primary-600={isTarget}
    class:border-primary-600={isTarget}
    class:ring-2={selected || connectedToSelected}
    class:ring-primary-500={selected}
    class:ring-[#26A69A]={connectedToSelected && !selected}
    class:opacity-30={isGhosted}
    class:pointer-events-none={isGhosted}
    title={label}
>
    {#if hiddenCount > 0}
        <button
            class="absolute -top-3 -right-3 bg-primary-50 text-primary-700 border border-primary-300 rounded-full px-2 py-0.5 text-[11px] font-semibold shadow-sm hover:bg-primary-100 transition"
            title={`${hiddenCount} hidden upstream model${hiddenCount === 1 ? "" : "s"} • click to expand`}
            onclick={(e) => {
                e.stopPropagation();
                expandHidden?.();
            }}
        >
            ⋯ {hiddenCount}
        </button>
    {/if}
    <Handle
        type="target"
        position={Position.Top}
        class="!opacity-0 !pointer-events-none !w-0 !h-0"
        isConnectable={false}
    />
    <Handle
        type="source"
        position={Position.Bottom}
        class="!opacity-0 !pointer-events-none !w-0 !h-0"
        isConnectable={false}
    />
    
    <div class="flex items-center justify-center">
        <span class="text-xs font-medium truncate block w-full" class:text-gray-900={!isTarget} class:text-white={isTarget}>{label}</span>
    </div>
</div>

