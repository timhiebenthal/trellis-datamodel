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
                                <strong class="flex items-center gap-1.5">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" class="inline-block flex-shrink-0">
                                        <g fill="none" stroke="currentColor" stroke-width="1.5">
                                            <path stroke-linecap="round" d="m17.458 9.08l-.291-.514c-.22-.389-.33-.583-.518-.66c-.187-.078-.399-.017-.822.106l-.72.206a1.16 1.16 0 0 1-.801-.102L14.107 8a1.2 1.2 0 0 1-.465-.581l-.197-.598c-.129-.396-.194-.594-.348-.708S12.738 6 12.33 6h-.658c-.41 0-.614 0-.768.113c-.154.114-.219.312-.348.708l-.197.598a1.2 1.2 0 0 1-.465.58l-.199.117c-.247.13-.53.165-.801.102l-.72-.206c-.423-.123-.635-.184-.822-.106c-.188.077-.298.271-.518.66l-.291.514c-.206.364-.31.547-.29.74c.02.194.159.35.435.663l.608.692c.149.191.254.525.254.825s-.105.633-.254.825l-.608.692h0c-.276.312-.415.468-.435.662s.084.377.29.74l.291.515c.22.388.33.583.518.66c.187.078.399.017.822-.106l.72-.206a1.16 1.16 0 0 1 .801.102l.199.116c.212.138.374.342.465.581l.197.599c.129.396.194.593.348.707s.359.113.768.113h.658c.41 0 .614 0 .768-.113c.154-.114.219-.311.348-.707l.197-.599c.09-.24.253-.443.465-.58l.199-.117c.247-.13.53-.165.801-.102l.72.206c.423.123.635.184.822.106c.188-.077.298-.272.518-.66h0l.291-.514c.206-.364.31-.547.29-.74c-.02-.195-.159-.35-.435-.663l-.608-.692c-.149-.191-.254-.525-.254-.825s.105-.634.254-.825l.608-.692c.276-.312.415-.469.434-.662s-.083-.377-.289-.74Z" />
                                            <circle cx="12" cy="12" r="1.75" />
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 2v2.859A9.97 9.97 0 0 0 12 2C6.477 2 2 6.477 2 12a10 10 0 0 0 .832 4M5 22v-2.859A9.97 9.97 0 0 0 12 22c5.523 0 10-4.477 10-10a10 10 0 0 0-.832-4" />
                                        </g>
                                    </svg>
                                    Setup Required
                                </strong><br />
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