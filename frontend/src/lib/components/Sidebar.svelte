<script lang="ts">
    import { dbtModels, configStatus } from "$lib/stores";
    import type { DbtModel, TreeNode } from "$lib/types";
    import SidebarGroup from "./SidebarGroup.svelte";
    import Icon from "@iconify/svelte";

    const { width = 260, loading = false } = $props<{
        width?: number;
        loading?: boolean;
    }>();

    let searchTerm = $state("");
    let collapsed = $state(false);

    let filteredModels = $derived(
        $dbtModels.filter((m) =>
            m.name.toLowerCase().includes(searchTerm.toLowerCase()),
        ),
    );

    let treeNodes = $derived(buildTree(filteredModels));

    function buildTree(models: DbtModel[]): TreeNode[] {
        const rootObj: any = { _files: [], _folders: {} };

        for (const model of models) {
            let p = model.file_path?.replace(/\\/g, '/') || "";
            const lastSlash = p.lastIndexOf('/');
            const dir = lastSlash !== -1 ? p.substring(0, lastSlash) : "";
            
            let parts = dir.split('/').filter(x => x !== "." && x !== "");
            if (parts[0] === "models") parts.shift();
            
            let current = rootObj;
            for (const part of parts) {
                if (!current._folders[part]) {
                    current._folders[part] = { _files: [], _folders: {} };
                }
                current = current._folders[part];
            }
            current._files.push(model);
        }

        function convert(obj: any, name: string, path: string): TreeNode {
             const folderNodes = Object.keys(obj._folders).map(key => 
                convert(obj._folders[key], key, path ? `${path}/${key}` : key)
             );
             const fileNodes = obj._files.map((m: DbtModel) => ({
                 name: m.name,
                 path: path ? `${path}/${m.name}` : m.name,
                 type: 'file',
                 children: [],
                 model: m
             }));
             
             folderNodes.sort((a: TreeNode, b: TreeNode) => a.name.localeCompare(b.name));
             fileNodes.sort((a: TreeNode, b: TreeNode) => a.name.localeCompare(b.name));

             return {
                 name,
                 path,
                 type: 'folder',
                 children: [...folderNodes, ...fileNodes]
             };
        }
        
        return convert(rootObj, "root", "").children;
    }

    function onDragStart(event: DragEvent, model: DbtModel) {
        if (!event.dataTransfer) return;
        // Set data to identify the drag source and payload
        event.dataTransfer.setData(
            "application/dbt-model",
            JSON.stringify(model),
        );
        event.dataTransfer.effectAllowed = "all";
    }

    function toggleCollapse() {
        collapsed = !collapsed;
    }
</script>

<aside
    class="bg-slate-50 h-full p-3 flex flex-col border-r border-slate-200 overflow-hidden flex-shrink-0 sidebar transition-all duration-300"
    style={`width:${collapsed ? 48 : width}px`}
>
    {#if collapsed}
        <button
            onclick={toggleCollapse}
            class="w-full h-10 flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-200 rounded transition-colors"
            title="Expand sidebar"
        >
            <Icon icon="lucide:chevron-right" class="w-5 h-5" />
        </button>
    {:else}
        <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-bold text-[#0f172a] uppercase tracking-wide">Explorer</h2>
            <button
                onclick={toggleCollapse}
                class="text-slate-400 hover:text-slate-700 p-1 hover:bg-slate-200 rounded transition-colors"
                title="Collapse sidebar"
            >
                <Icon icon="lucide:chevron-left" class="w-4 h-4" />
            </button>
        </div>

        <div class="relative mb-3">
            <div class="absolute left-2.5 top-2 text-slate-400">
                 <Icon icon="lucide:search" class="w-4 h-4" />
            </div>
            <input
                type="text"
                placeholder="Search models..."
                bind:value={searchTerm}
                class="w-full pl-8 pr-2 py-1.5 border border-slate-200 rounded bg-white text-sm focus:outline-none focus:ring-1 focus:ring-[#26A69A]"
            />
        </div>

        <div class="flex-1 overflow-y-auto pr-1 space-y-0.5">
            {#each treeNodes as node (node.path)}
                <SidebarGroup {node} {onDragStart} />
            {/each}
            {#if filteredModels.length === 0}
                {#if loading}
                    <div class="text-center mt-10">
                        <div
                            class="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-[#0f172a] mb-2"
                        ></div>
                        <div class="text-slate-500 text-sm italic">
                            Loading...
                        </div>
                    </div>
                {:else if $dbtModels.length === 0}
                    <div class="text-center mt-10 px-2">
                        <div class="text-slate-500 text-sm mb-4">
                            No models found
                        </div>
                        {#if $configStatus && (!$configStatus.config_present || !$configStatus.dbt_project_path || !$configStatus.manifest_exists)}
                            <div
                                class="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800 text-left"
                            >
                                <strong>📍 Setup Required</strong><br />
                                {#if !$configStatus.config_present}
                                    Missing <code>config.yml</code>.
                                {:else if !$configStatus.dbt_project_path}
                                    Set <code>dbt_project_path</code> in config.
                                {:else if !$configStatus.manifest_exists}
                                    Manifest not found.<br />
                                    <span class="text-[10px] mt-1 block opacity-75"
                                        >Check <code>dbt_project_path</code>.</span
                                    >
                                {/if}
                            </div>
                        {/if}
                    </div>
                {:else}
                    <div class="text-slate-400 text-sm text-center mt-10 italic">
                        No matches found
                    </div>
                {/if}
            {/if}
        </div>
    {/if}
</aside>