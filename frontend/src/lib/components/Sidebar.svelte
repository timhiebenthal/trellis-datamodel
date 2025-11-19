<script lang="ts">
    import { dbtModels } from '$lib/stores';
    import type { DbtModel } from '$lib/types';

    let searchTerm = $state(""); 

    let filteredModels = $derived($dbtModels.filter(m => 
        m.name.toLowerCase().includes(searchTerm.toLowerCase())
    ));

    function onDragStart(event: DragEvent, model: DbtModel) {
        if (!event.dataTransfer) return;
        // Set data to identify the drag source and payload
        event.dataTransfer.setData('application/dbt-model', JSON.stringify(model));
        event.dataTransfer.effectAllowed = 'copy';
    }
</script>

<aside class="w-64 bg-gray-100 h-full p-4 flex flex-col border-r overflow-hidden">
    <h2 class="text-lg font-bold mb-4 text-gray-800">dbt Models</h2>
    <input 
        type="text" 
        placeholder="Search models..." 
        bind:value={searchTerm}
        class="w-full p-2 border rounded mb-4 bg-white text-sm"
    />
    
    <div class="flex-1 overflow-y-auto space-y-2 pr-1">
        {#each filteredModels as model (model.name)}
            <div 
                class="p-3 bg-white rounded shadow-sm cursor-move hover:shadow-md border border-gray-200 hover:border-blue-400 transition-all select-none"
                draggable="true"
                ondragstart={(e) => onDragStart(e, model)}
                role="listitem"
            >
                <div class="font-medium text-sm text-gray-900 truncate" title={model.name}>{model.name}</div>
                <div class="text-xs text-gray-500 truncate">{model.schema}.{model.table}</div>
            </div>
        {/each}
        {#if filteredModels.length === 0}
            <div class="text-gray-500 text-sm text-center mt-10 italic">
                {$dbtModels.length === 0 ? 'Loading or no models...' : 'No matches found'}
            </div>
        {/if}
    </div>
</aside>

