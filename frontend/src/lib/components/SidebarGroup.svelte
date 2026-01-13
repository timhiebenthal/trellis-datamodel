<script lang="ts">
    import type { DbtModel, TreeNode, EntityData } from "$lib/types";
    import SidebarGroup from "./SidebarGroup.svelte";
    import Icon from "@iconify/svelte";
    import { folderFilter, nodes, modelingStyle, dimensionPrefixes, factPrefixes } from "$lib/stores";
    import { extractRelativePath, toggleFolderFilter } from "$lib/utils/folder-utils";
    import { classifyModelTypeFromPrefixes } from "$lib/utils";

    let { node, onDragStart, mainFolderPrefix = "" } = $props<{
        node: TreeNode;
        onDragStart: (event: DragEvent, model: DbtModel) => void;
        mainFolderPrefix?: string;
    }>();
    
    let collapsed = $state(false);
    
    // Check if current model is bound to any entity - use $state to avoid derived recalculations
    let isModelBound = $state(false);
    
    // Update isModelBound when nodes changes
    $effect(() => {
        const currentNodes = $nodes;
        if (node.model) {
            isModelBound = currentNodes.some((n) => {
                if (n.type !== 'entity') return false;
                const data = n.data as unknown as EntityData;
                const primaryMatch = data.dbt_model === node.model!.unique_id;
                const additionalMatch = (data.additional_models || []).includes(node.model!.unique_id);
                return primaryMatch || additionalMatch;
            });
        }
    });
    
    // Extract of relative folder path for filtering
    let filterPath = $derived(extractRelativePath(node.path));

    // Determine icon based on modeling style and model name
    let modelIcon = $derived(() => {
        if (!node.model) return 'lucide:database';

        // In entity_model mode, always use database icon
        if ($modelingStyle !== 'dimensional_model') {
            return 'lucide:database';
        }

        // In dimensional_model mode, classify based on prefix
        const type = classifyModelTypeFromPrefixes(
            node.model.name,
            $dimensionPrefixes,
            $factPrefixes
        );

        switch (type) {
            case 'dimension':
                return 'lucide:list';
            case 'fact':
                return 'lucide:bar-chart-3';
            default:
                return 'lucide:circle-dashed';
        }
    });

    // Determine icon color based on modeling style and model type
    let modelIconColor = $derived(() => {
        if (!node.model || $modelingStyle !== 'dimensional_model') {
            return 'text-gray-400 group-hover:text-primary-600';
        }

        const type = classifyModelTypeFromPrefixes(
            node.model.name,
            $dimensionPrefixes,
            $factPrefixes
        );

        switch (type) {
            case 'dimension':
                return 'text-green-600 group-hover:text-primary-600';
            case 'fact':
                return 'text-blue-600 group-hover:text-primary-600';
            default:
                return 'text-gray-500 group-hover:text-primary-600';
        }
    });

    function toggle(event: MouseEvent) {
        // Only toggle on chevron/folder icon click, not on the whole button
        const target = event.target as HTMLElement;
        if (target.closest('.toggle-icon')) {
            collapsed = !collapsed;
        }
    }

    function handleFolderClick(event: MouseEvent) {
        const target = event.target as HTMLElement;
        if (!target.closest('.toggle-icon') && filterPath) {
            // Clicked on folder name, toggle filter
            $folderFilter = toggleFolderFilter($folderFilter, filterPath);
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
        <Icon icon={modelIcon()} class="w-3.5 h-3.5 {modelIconColor()} transition-colors flex-shrink-0" />
        <span class="flex-1 truncate">{node.name}</span>
        {#if isModelBound}
            <Icon icon="mdi:check" class="w-3.5 h-3.5 text-success-600 flex-shrink-0" />
        {/if}
    </div>
{/if}
