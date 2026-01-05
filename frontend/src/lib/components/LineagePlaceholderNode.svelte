<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";
    import Icon from "@iconify/svelte";

    let { data, selected }: NodeProps = $props();

    const label = $derived((data?.label as string) || "Expand");
    const hiddenCount = $derived((data?.hiddenCount as number) || 0);
    const tooltipText = $derived(
        hiddenCount > 0 
            ? `${hiddenCount} hidden upstream model${hiddenCount !== 1 ? 's' : ''} - click to expand`
            : "Click to expand hidden upstream models"
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
    class="rounded-lg border-2 border-primary-400 shadow-md px-4 py-2 bg-primary-50 text-primary-700 text-sm font-semibold select-none cursor-pointer hover:bg-primary-100 hover:border-primary-500 transition-colors"
    class:ring-2={selected}
    class:ring-primary-600={selected}
    onclick={handleClick}
    onkeydown={handleKeydown}
    role="button"
    tabindex="0"
    aria-label="Expand lineage"
    title={tooltipText}
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

    <div class="flex items-center gap-2">
        <Icon icon="lucide:chevrons-up" class="w-4 h-4 flex-shrink-0" />
        <span class="truncate">{label}</span>
        {#if hiddenCount > 0}
            <span class="text-xs bg-primary-200 text-primary-800 px-1.5 py-0.5 rounded-full font-bold">{hiddenCount}</span>
        {/if}
    </div>
</div>


