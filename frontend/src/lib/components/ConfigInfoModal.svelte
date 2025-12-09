<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { ConfigInfo } from "$lib/types";

    const { open = false, info = null, loading = false, error = null, onClose, onRetry } =
        $props<{
            open: boolean;
            info: ConfigInfo | null;
            loading: boolean;
            error: string | null;
            onClose: () => void;
            onRetry: () => void;
        }>();
</script>

{#if open}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-3xl border border-gray-200">
            <div class="px-5 py-4 flex items-center justify-between border-b border-gray-200">
                <div class="flex items-center gap-2">
                    <Icon icon="lucide:info" class="w-5 h-5 text-primary-600" />
                    <h2 class="text-lg font-semibold text-gray-900">Configuration Info</h2>
                </div>
                <button
                    class="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                    onclick={onClose}
                    aria-label="Close"
                >
                    <Icon icon="lucide:x" class="w-5 h-5" />
                </button>
            </div>

            <div class="p-5 space-y-4 max-h-[70vh] overflow-y-auto text-sm text-gray-800">
                {#if loading}
                    <div class="flex items-center gap-3 text-gray-600">
                        <Icon icon="lucide:loader-2" class="w-5 h-5 animate-spin" />
                        <span>Loading configuration...</span>
                    </div>
                {:else if error}
                    <div class="flex items-center gap-3 text-danger-700 bg-danger-50 border border-danger-200 rounded-lg px-3 py-2">
                        <Icon icon="lucide:alert-triangle" class="w-5 h-5" />
                        <span>{error}</span>
                        <button
                            class="ml-auto px-3 py-1 text-sm rounded-md bg-danger-600 text-white hover:bg-danger-700"
                            onclick={onRetry}
                        >
                            Retry
                        </button>
                    </div>
                {:else if info}
                    {#each [
                        { label: "Config file", value: info.config_path || "Not found" },
                        { label: "Framework", value: info.framework },
                        { label: "dbt project path", value: info.dbt_project_path },
                        { label: "Manifest path", value: info.manifest_path, exists: info.manifest_exists },
                        { label: "Catalog path", value: info.catalog_path, exists: info.catalog_exists },
                        { label: "Data model path", value: info.data_model_path, exists: info.data_model_exists },
                        { label: "Canvas layout path", value: info.canvas_layout_path, exists: info.canvas_layout_exists },
                        { label: "Frontend build dir", value: info.frontend_build_dir },
                        {
                            label: "Configured model paths",
                            value: info.model_paths_configured.length
                                ? info.model_paths_configured.join(", ")
                                : "None",
                        },
                        {
                            label: "Resolved model dirs",
                            value: info.model_paths_resolved.length
                                ? info.model_paths_resolved.join(", ")
                                : "None",
                        },
                    ] as row (row.label)}
                        <div class="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 flex flex-col gap-1">
                            <span class="text-xs uppercase tracking-wide text-gray-500 font-semibold">{row.label}</span>
                            <div class="flex items-center gap-2">
                                <span class="text-sm text-gray-900 break-all">{row.value}</span>
                                {#if row.exists !== undefined}
                                    {#if row.exists}
                                        <span class="text-[10px] font-semibold text-success-700 bg-success-50 border border-success-200 rounded-full px-2 py-0.5">Exists</span>
                                    {:else}
                                        <span class="text-[10px] font-semibold text-danger-700 bg-danger-50 border border-danger-200 rounded-full px-2 py-0.5">Missing</span>
                                    {/if}
                                {/if}
                            </div>
                        </div>
                    {/each}
                {:else}
                    <div class="text-gray-500">No configuration info available.</div>
                {/if}
            </div>

            <div class="px-5 py-3 border-t border-gray-200 flex justify-end">
                <button
                    class="px-4 py-2 text-sm font-medium bg-gray-100 text-gray-800 rounded-lg hover:bg-gray-200"
                    onclick={onClose}
                >
                    Close
                </button>
            </div>
        </div>
    </div>
{/if}

