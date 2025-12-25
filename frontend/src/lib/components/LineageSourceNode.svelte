<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";

    let { data, selected }: NodeProps = $props();
    
    const label = $derived((data?.label as string) || '');
</script>

<div
    class="rounded-lg border-2 bg-blue-50 border-blue-400 shadow-md px-3 py-2 min-w-[120px] max-w-[200px] text-center"
    class:ring-2={selected}
    class:ring-blue-500={selected}
    title={label}
>
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
    
    <div class="flex flex-col items-center gap-1 w-full">
        <div class="flex items-center gap-2 justify-center w-full">
            <span class="text-xs font-semibold text-blue-600 uppercase tracking-wide whitespace-nowrap">RAW</span>
            {#if data.sourceName}
                <span class="text-xs text-blue-700 opacity-75 font-mono truncate max-w-[100px]">{data.sourceName}</span>
            {/if}
        </div>
        <div class="flex items-center gap-2 justify-center w-full">
            <span class="text-xs font-medium text-blue-900 truncate block w-full">{label}</span>
        </div>
    </div>
</div>

