<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";

    let { data, selected }: NodeProps = $props();
</script>

<div
    class="rounded-lg border-2 bg-blue-50 border-blue-400 shadow-md px-3 py-2 min-w-[120px] text-center"
    class:ring-2={selected}
    class:ring-blue-500={selected}
>
    <Handle type="target" position={Position.Top} class="!bg-blue-400 !w-2 !h-2" />
    <Handle type="source" position={Position.Bottom} class="!bg-blue-400 !w-2 !h-2" />
    
    <div class="flex flex-col items-center gap-1">
        <div class="flex items-center gap-2 justify-center">
            <span class="text-xs font-semibold text-blue-600 uppercase tracking-wide">RAW</span>
            {#if data.sourceName}
                <span class="text-xs text-blue-700 opacity-75 font-mono">{data.sourceName}</span>
            {/if}
        </div>
        <div class="flex items-center gap-2 justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" class="text-blue-600">
                <path fill="currentColor" d="M3 15V9h3.5q.6 0 1.05.45T8 10.5v1q0 .45-.238.813T7.1 12.9L8 15H6.5l-.9-2H4.5v2zm5.75 0l1.5-6h2.5l1.5 6h-1.5l-.35-1.5h-1.75l-.4 1.5zm6.75 0L14 9h1.5l.75 3L17 9h1.5l.75 3L20 9h1.5L20 15h-1.5l-.75-3.05L17 15zM11 12h1l-.25-1h-.5zm-6.5-.5h2v-1h-2z"/>
            </svg>
            <span class="text-sm font-medium text-blue-900">{data.label}</span>
        </div>
    </div>
</div>

