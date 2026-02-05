<script lang="ts">
    import Icon from "@iconify/svelte";
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";

    let { data, selected }: NodeProps = $props();

    const label = $derived((data?.label as string) || "Expand");
    const displayLabel = $derived(label === "..." ? "More" : label);
    const tooltip = $derived(
        (data?.tooltip as string) || "Expand lineage to reveal hidden models"
    );

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
    class="group inline-flex items-center gap-1.5 rounded-full border-2 border-dashed border-gray-300 bg-white text-gray-800 text-xs font-semibold shadow-sm px-3 py-1 select-none cursor-pointer max-w-[180px] transition-colors hover:bg-primary-50 hover:border-primary-400 hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
    class:ring-2={selected}
    class:ring-primary-500={selected}
    onclick={handleClick}
    onkeydown={handleKeydown}
    role="button"
    tabindex="0"
    aria-label="Expand lineage to reveal hidden models"
    title={tooltip}
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

    <Icon icon="lucide:plus-circle" class="w-3.5 h-3.5 text-primary-600" />
    <span class="truncate block">{displayLabel}</span>
</div>


