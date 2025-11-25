<script lang="ts">
    import { dbtModels, configStatus } from "$lib/stores";
    import type { DbtModel } from "$lib/types";

    const { width = 260, loading = false } = $props<{
        width?: number;
        loading?: boolean;
    }>();

    let searchTerm = $state("");

    let filteredModels = $derived(
        $dbtModels.filter((m) =>
            m.name.toLowerCase().includes(searchTerm.toLowerCase()),
        ),
    );

    function onDragStart(event: DragEvent, model: DbtModel) {
        if (!event.dataTransfer) return;
        // Set data to identify the drag source and payload
        event.dataTransfer.setData(
            "application/dbt-model",
            JSON.stringify(model),
        );
        event.dataTransfer.effectAllowed = "all";
    }
</script>

<aside
    class="bg-gray-100 h-full p-3 flex flex-col border-r overflow-hidden flex-shrink-0 sidebar"
    style={`width:${width}px`}
>
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
            {#if loading}
                <div class="text-center mt-10">
                    <div
                        class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-400 mb-2"
                    ></div>
                    <div class="text-gray-500 text-sm italic">
                        Loading models...
                    </div>
                </div>
            {:else if $dbtModels.length === 0}
                <div class="text-center mt-10 px-2">
                    <div class="text-gray-500 text-sm mb-4">
                        No models found
                    </div>
                    {#if $configStatus && (!$configStatus.config_present || !$configStatus.dbt_project_path || !$configStatus.manifest_exists)}
                        <div
                            class="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-700 text-left"
                        >
                            <strong>📍 Configuration Info</strong><br />
                            {#if !$configStatus.config_present}
                                No <code>config.yaml</code> found.
                            {:else if !$configStatus.dbt_project_path}
                                Set <code>dbt_project_path</code> in
                                <code>config.yaml</code> to load your dbt models.
                            {:else if !$configStatus.manifest_exists}
                                Manifest not found at:<br />
                                <span class="font-mono text-[10px] break-all"
                                    >{$configStatus.manifest_path}</span
                                ><br />
                                <span class="text-[10px] mt-1 block"
                                    >Please verify your <code
                                        >dbt_project_path</code
                                    > points to the correct location.</span
                                >
                            {/if}
                        </div>
                    {/if}
                </div>
            {:else}
                <div class="text-gray-500 text-sm text-center mt-10 italic">
                    No matches found
                </div>
            {/if}
        {/if}
    </div>
</aside>
