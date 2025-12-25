<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";

    let { data, selected }: NodeProps = $props();

    const label = $derived((data?.label as string) || "Expand");

    function handleClick(event: MouseEvent) {
        event.stopPropagation();
        if (typeof data?.onClick === "function") (data.onClick as () => void)();
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            // Re-use click logic
            handleClick(event as unknown as MouseEvent);
        }
    }
</script>

<div
    class="rounded-full border-2 border-dashed shadow-sm px-3 py-1 bg-gray-50 text-gray-700 text-xs font-semibold select-none cursor-pointer max-w-[150px]"
    class:ring-2={selected}
    class:ring-primary-500={selected}
    onclick={handleClick}
    onkeydown={handleKeydown}
    role="button"
    tabindex="0"
    aria-label="Expand lineage"
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

    <span class="truncate block">{label}</span>
</div>


