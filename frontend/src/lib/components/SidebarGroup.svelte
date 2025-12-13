<script lang="ts">
    import type { DbtModel, TreeNode } from "$lib/types";
    import SidebarGroup from "./SidebarGroup.svelte"; 
    import Icon from "@iconify/svelte";
    import { folderFilter } from "$lib/stores";

    let { node, onDragStart, mainFolderPrefix = "" } = $props<{
        node: TreeNode;
        onDragStart: (event: DragEvent, model: DbtModel) => void;
        mainFolderPrefix?: string;
    }>();
    
    let collapsed = $state(false);
    
    function toggle(event: MouseEvent) {
        // Only toggle on chevron/folder icon click, not on the whole button
        const target = event.target as HTMLElement;
        if (target.closest('.toggle-icon')) {
            collapsed = !collapsed;
        }
    }

    function handleFolderClick(event: MouseEvent) {
        const target = event.target as HTMLElement;
        if (!target.closest('.toggle-icon')) {
            // Clicked on folder name, set filter
            const folderPath = node.path.replace(/^[^/]+\//, ''); // Remove first segment
            if (folderPath && folderPath !== node.path) {
                const prev = $folderFilter as unknown;
                const prevArr = Array.isArray(prev) ? (prev as string[]) : [];
                const next = prevArr.includes(folderPath)
                    ? prevArr.filter((f) => f !== folderPath)
                    : [...prevArr, folderPath];
                $folderFilter = next;
            }
        }
    }
</script>

{#if node.type === 'folder'}
    <div class="pl-0">
        <button 
            class="flex items-center w-full py-1 px-2 cursor-pointer hover:bg-gray-200/50 text-xs font-semibold text-gray-600 select-none text-left rounded-md transition-colors"
            onclick={(e) => {toggle(e); handleFolderClick(e);}}
            type="button"
        >
            <span class="mr-1.5 w-3 h-3 flex items-center justify-center transition-transform {collapsed ? '-rotate-90' : 'rotate-0'} toggle-icon">
                <Icon icon="lucide:chevron-down" class="w-3 h-3 text-gray-400" />
            </span>
            <span class="mr-1.5 flex-shrink-0 toggle-icon">
                {#if collapsed}
                    <Icon icon="lucide:folder" class="w-3.5 h-3.5 text-gray-400" />
                {:else}
                    <Icon icon="lucide:folder-open" class="w-3.5 h-3.5 text-gray-400" />
                {/if}
            </span>
            <span class="truncate hover:text-primary-600 transition-colors" title="Click to filter by folder: {node.name}">{node.name}</span>
        </button>
        {#if !collapsed}
            <div class="border-l border-gray-200 ml-[11px] pl-1">
                {#each node.children as child (child.path)}
                    <SidebarGroup node={child} {onDragStart} mainFolderPrefix={mainFolderPrefix} />
                {/each}
            </div>
        {/if}
    </div>
{:else if node.model}
    <div
        class="ml-5 px-2 py-1.5 bg-white rounded-md cursor-move hover:shadow-sm border border-gray-200 hover:border-primary-600 transition-all select-none text-xs font-medium text-gray-700 truncate flex items-center gap-1.5 mb-1 group"
        draggable="true"
        ondragstart={(e) => onDragStart(e, node.model!)}
        role="listitem"
        title={`${node.name} (${node.model.schema}.${node.model.table})`}
    >
        <Icon icon="lucide:database" class="w-3.5 h-3.5 text-gray-400 group-hover:text-primary-600 transition-colors flex-shrink-0" />
        {node.name}
    </div>
{/if}