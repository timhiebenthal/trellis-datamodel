<script lang="ts">
    import type { DbtModel, TreeNode } from "$lib/types";
    import SidebarGroup from "./SidebarGroup.svelte"; 

    let { node, onDragStart } = $props<{
        node: TreeNode;
        onDragStart: (event: DragEvent, model: DbtModel) => void;
    }>();
    
    let collapsed = $state(false);
    
    function toggle() {
        collapsed = !collapsed;
    }
</script>

{#if node.type === 'folder'}
    <div class="pl-0">
        <button 
            class="flex items-center w-full py-1 px-2 cursor-pointer hover:bg-gray-200 text-xs font-semibold text-gray-700 select-none text-left"
            onclick={toggle}
            type="button"
        >
            <span class="mr-1 w-3 h-3 flex items-center justify-center transform transition-transform {collapsed ? '-rotate-90' : 'rotate-0'}">
                <svg class="w-2.5 h-2.5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"/>
                </svg>
            </span>
            <svg class="w-3.5 h-3.5 mr-1.5 text-yellow-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                 <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
            </svg>
            <span class="truncate" title={node.name}>{node.name}</span>
        </button>
        {#if !collapsed}
            <div class="border-l border-gray-300 ml-[11px] pl-1">
                {#each node.children as child (child.path)}
                    <SidebarGroup node={child} {onDragStart} />
                {/each}
            </div>
        {/if}
    </div>
{:else if node.model}
    <div
        class="ml-5 px-2 py-1.5 bg-white rounded cursor-move hover:shadow border border-gray-200 hover:border-blue-400 transition-all select-none text-xs font-medium text-gray-900 truncate flex items-center gap-1.5 mb-1"
        draggable="true"
        ondragstart={(e) => onDragStart(e, node.model!)}
        role="listitem"
        title={`${node.model.name} (${node.model.schema}.${node.model.table})`}
    >
        <svg class="w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        {node.model.name}
    </div>
{/if}

