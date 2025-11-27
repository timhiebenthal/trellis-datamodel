<script lang="ts">
    import {
        Handle,
        Position,
        useSvelteFlow,
        type NodeProps,
    } from "@xyflow/svelte";
    import { nodes, edges } from "$lib/stores";
    import Icon from "@iconify/svelte";

    type $$Props = NodeProps;

    let { data, id, selected } = $props<$$Props>();

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
        class="inline-flex items-center gap-1.5 px-2 py-1 bg-slate-200 hover:bg-slate-300 rounded cursor-pointer transition-colors text-xs shadow-sm"
        onclick={toggleCollapse}
    >
        <Icon icon="lucide:chevron-right" class="w-3 h-3 text-slate-500" />
        <Icon icon="lucide:folder" class="w-3 h-3 text-slate-500" />
        <span class="font-medium text-slate-700">{data.label || id}</span>
        <span class="text-slate-500 bg-slate-300 px-1 rounded text-[10px]">{childCount}</span>
    </div>
{:else}
    <!-- Full container when expanded -->
    <div
        class="group-node rounded-lg bg-slate-100/70"
        style={`width:${data.width ?? 300}px; height:${data.height ?? 200}px;`}
    >
        <div
            class="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-200/50 transition-colors text-xs rounded-t-lg"
            onclick={toggleCollapse}
        >
            <Icon icon="lucide:chevron-down" class="w-3 h-3 text-slate-500" />
            <Icon icon="lucide:folder" class="w-3 h-3 text-slate-500" />
            <span class="font-medium text-slate-700">{data.label || id}</span>
            <span class="text-slate-400 bg-slate-200 px-1.5 py-0.5 rounded text-[10px]">{childCount}</span>
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
