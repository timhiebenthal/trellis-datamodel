<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";

    let { data, selected }: NodeProps = $props();
    
    const isTarget = data.level === 0;
</script>

<div
    class="rounded-lg border-2 shadow-md px-3 py-2 min-w-[120px] max-w-[200px] text-center"
    class:bg-white={!isTarget}
    class:border-gray-300={!isTarget}
    class:bg-primary-600={isTarget}
    class:border-primary-600={isTarget}
    class:ring-2={selected}
    class:ring-primary-500={selected}
    title={data.label}
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
    
    <div class="flex items-center justify-center">
        <span class="text-sm font-medium truncate block w-full" class:text-gray-900={!isTarget} class:text-white={isTarget}>{data.label}</span>
    </div>
</div>

