<script lang="ts">
    import { dbtModels } from '$lib/stores';
    import type { DbtModel } from '$lib/types';

    const { width = 260 } = $props<{ width?: number }>();

    let searchTerm = $state(""); 

    let filteredModels = $derived($dbtModels.filter(m => 
        m.name.toLowerCase().includes(searchTerm.toLowerCase())
    ));

    function onDragStart(event: DragEvent, model: DbtModel) {
        if (!event.dataTransfer) return;
        // Set data to identify the drag source and payload
        event.dataTransfer.setData('application/dbt-model', JSON.stringify(model));
        event.dataTransfer.effectAllowed = 'all';
    }
</script>

<aside class="bg-gray-100 h-full p-3 flex flex-col border-r overflow-hidden flex-shrink-0 sidebar" style={`width:${width}px`}>
    <h2 class="text-base font-semibold mb-3 text-gray-800">dbt Models</h2>
    <input 
        type="text" 
        placeholder="Search models..." 
        bind:value={searchTerm}
        class="w-full px-2 py-1.5 border rounded mb-3 bg-white text-sm"
    />
    
    <div class="flex-1 overflow-y-auto pr-1 space-y-1.5">
        {#each filteredModels as model (model.name)}
            <div 
                class="px-2 py-1 bg-white rounded cursor-move hover:shadow border border-gray-200 hover:border-blue-400 transition-all select-none text-xs font-medium text-gray-900 truncate"
                draggable="true"
                ondragstart={(e) => onDragStart(e, model)}
                role="listitem"
                title={`${model.name} (${model.schema}.${model.table})`}
            >
                {model.name}
            </div>
        {/each}
        {#if filteredModels.length === 0}
            <div class="text-gray-500 text-sm text-center mt-10 italic">
                {$dbtModels.length === 0 ? 'Loading or no models...' : 'No matches found'}
            </div>
        {/if}
    </div>
</aside>

