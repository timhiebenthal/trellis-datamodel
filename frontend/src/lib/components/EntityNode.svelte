<script lang="ts">
    import { Handle, Position, useSvelteFlow, type NodeProps } from '@xyflow/svelte';
    import { viewMode, dbtModels } from '$lib/stores';
    import type { DbtModel } from '$lib/types';

    type $$Props = NodeProps;

    let { data, id } = $props<$$Props>();
    
    const { updateNodeData } = useSvelteFlow();
    
    // Reactive binding check
    let boundModelName = $derived(data.dbt_model as string | undefined);
    let isBound = $derived(!!boundModelName);
    
    // Find model details
    let modelDetails = $derived(
        isBound ? $dbtModels.find(m => m.name === boundModelName) : null
    );

    function updateLabel(e: Event) {
        const label = (e.target as HTMLInputElement).value;
        updateNodeData(id, { label });
    }
    
    function updateDescription(e: Event) {
        const description = (e.target as HTMLTextAreaElement).value;
        updateNodeData(id, { description });
    }

    function onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        const json = event.dataTransfer?.getData('application/dbt-model');
        if (!json) return;
        const model: DbtModel = JSON.parse(json);
        
        updateNodeData(id, { dbt_model: model.name });
    }
    
    function onDragOver(event: DragEvent) {
        event.preventDefault();
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'link';
        }
    }
    
    function unbind() {
        updateNodeData(id, { dbt_model: null });
    }
</script>

<div 
    class="rounded-md border-2 bg-white min-w-[220px] shadow-sm transition-all hover:shadow-md"
    class:border-green-500={isBound}
    class:border-gray-300={!isBound}
    ondrop={onDrop}
    ondragover={onDragOver}
    role="presentation"
>
    <Handle type="target" position={Position.Top} class="!bg-gray-400 !w-3 !h-3" />
    
    <!-- Header -->
    <div class="p-2 border-b border-gray-100 bg-gray-50 rounded-t-md flex justify-between items-center">
        <input 
            value={data.label} 
            oninput={updateLabel}
            class="font-bold bg-transparent w-full focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-300 rounded px-1 text-sm"
            placeholder="Entity Name"
        />
        {#if isBound}
            <div class="w-2 h-2 rounded-full bg-green-500 ml-2 flex-shrink-0" title="Bound to {boundModelName}"></div>
        {/if}
    </div>

    <!-- Body -->
    <div class="p-2">
        {#if $viewMode === 'physical' && isBound && modelDetails}
            <div class="text-xs">
                <div class="font-mono text-gray-600 mb-2 bg-gray-100 p-1 rounded break-all">
                    {modelDetails.schema}.{modelDetails.table}
                </div>
                <div class="max-h-40 overflow-y-auto border rounded bg-gray-50 p-1 scrollbar-thin">
                    {#each modelDetails.columns as col}
                        <div class="flex justify-between py-1 border-b border-gray-200 last:border-0">
                            <span class="font-medium text-gray-700 truncate pr-2" title={col.name}>{col.name}</span>
                            <span class="text-gray-400 text-[10px] uppercase">{col.type}</span>
                        </div>
                    {/each}
                </div>
                <button 
                    class="mt-2 w-full text-xs text-red-500 hover:bg-red-50 p-1 rounded border border-red-100 transition-colors"
                    onclick={unbind}
                >
                    Unbind Model
                </button>
            </div>
        {:else}
            <!-- Concept View -->
             <textarea 
                value={data.description || ''} 
                oninput={updateDescription}
                class="w-full text-xs text-gray-600 resize-y min-h-[60px] focus:outline-none focus:bg-gray-50 focus:ring-1 focus:ring-blue-300 rounded p-1"
                placeholder="Description..."
            ></textarea>
            {#if isBound}
                 <div class="mt-2 text-xs text-green-600 flex items-center justify-between bg-green-50 p-1 rounded border border-green-100">
                    <span class="truncate font-medium" title={boundModelName}>🔗 {boundModelName}</span>
                    <button onclick={unbind} class="text-red-400 hover:text-red-600 ml-1 px-1">×</button>
                 </div>
            {:else}
                <div class="mt-2 text-[10px] text-gray-400 text-center border border-dashed border-gray-300 rounded p-2 bg-gray-50 pointer-events-none">
                    Drag dbt model here
                </div>
            {/if}
        {/if}
    </div>

    <Handle type="source" position={Position.Bottom} class="!bg-gray-400 !w-3 !h-3" />
</div>

