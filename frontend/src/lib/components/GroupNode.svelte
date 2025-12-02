<script lang="ts">
    import {
        Handle,
        Position,
        useSvelteFlow,
        type NodeProps,
    } from "@xyflow/svelte";
    import { nodes, edges } from "$lib/stores";
    import Icon from "@iconify/svelte";

    let { data, id, selected }: NodeProps = $props();

    const { updateNodeData } = useSvelteFlow();
    let isCollapsed = $derived(data.collapsed ?? false);

    function toggleCollapse() {
        const newCollapsed = !isCollapsed;
        updateNodeData(id, { collapsed: newCollapsed });
        
        // Get child node IDs
        const childIds = new Set($nodes.filter(n => n.parentId === id).map(n => n.id));
        
        // Hide/show child nodes
        $nodes = $nodes.map(n => {
            if (n.parentId === id) {
                return { ...n, hidden: newCollapsed };
            }
            return n;
        });
        
        // Hide/show edges connected to child nodes
        $edges = $edges.map(e => {
            if (childIds.has(e.source) || childIds.has(e.target)) {
                return { ...e, hidden: newCollapsed };
            }
            return e;
        });
    }

    // Count children
    let childCount = $derived(
        $nodes.filter(n => n.parentId === id).length
    );
</script>

{#if isCollapsed}
    <!-- Compact badge when collapsed -->
    <div
        class="inline-flex items-center gap-1.5 px-2 py-1 bg-gray-200 hover:bg-gray-300 border border-gray-300 rounded cursor-pointer transition-colors text-xs shadow-sm"
        onclick={toggleCollapse}
    >
        <Icon icon="lucide:chevron-right" class="w-3 h-3 text-gray-600" />
        <Icon icon="lucide:folder" class="w-3 h-3 text-gray-600" />
        <span class="font-medium text-gray-800">{data.label || id}</span>
        <span class="text-gray-700 bg-gray-300 px-1 rounded text-[10px]">{childCount}</span>
    </div>
{:else}
    <!-- Full container when expanded -->
    <div
        class="group-node rounded-xl bg-gray-200/50 border border-gray-300"
        style={`width:${data.width ?? 300}px; height:${data.height ?? 200}px;`}
    >
        <div
            class="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-200/70 transition-colors text-xs rounded-t-xl"
            onclick={toggleCollapse}
        >
            <Icon icon="lucide:chevron-down" class="w-3 h-3 text-gray-600" />
            <Icon icon="lucide:folder" class="w-3 h-3 text-gray-600" />
            <span class="font-medium text-gray-800">{data.label || id}</span>
            <span class="text-gray-700 bg-gray-300/80 px-1.5 py-0.5 rounded text-[10px]">{childCount}</span>
        </div>
    </div>
{/if}

<style>
    /* Override Svelte Flow's default node wrapper border */
    :global(.svelte-flow__node-group) {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }
</style>
