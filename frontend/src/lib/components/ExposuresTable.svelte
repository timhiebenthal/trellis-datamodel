<script lang="ts">
    import { onMount } from 'svelte';
    import { nodes, viewMode } from '$lib/stores';
    import { getExposures } from '$lib/api';
    import type { Exposure, EntityUsage, EntityData } from '$lib/types';
    import Icon from '@iconify/svelte';

    let exposures = $state<Exposure[]>([]);
    let entityUsage = $state<EntityUsage>({});
    let loading = $state(true);
    let error = $state<string | null>(null);

    // Derive entities from nodes (filter out group nodes)
    let entities = $derived(
        $nodes
            .filter((n) => n.type !== 'group')
            .map((n) => ({
                id: n.id,
                label: ((n.data as EntityData)?.label || '').trim() || 'Entity',
            }))
            .sort((a, b) => a.label.localeCompare(b.label))
    );

    // Map exposure types to icons
    function getExposureIcon(type?: string): string {
        switch (type?.toLowerCase()) {
            case 'dashboard':
                return 'mdi:view-dashboard';
            case 'notebook':
                return 'mdi:notebook';
            case 'application':
                return 'mdi:application';
            case 'analysis':
                return 'mdi:chart-line';
            default:
                return 'mdi:file-document';
        }
    }

    async function loadExposures() {
        // Only fetch if we're in exposures view mode
        if ($viewMode !== 'exposures') return;

        loading = true;
        error = null;
        try {
            const data = await getExposures();
            exposures = data.exposures;
            entityUsage = data.entityUsage;
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load exposures';
            console.error('Error loading exposures:', e);
        } finally {
            loading = false;
        }
    }

    // Fetch data when view mode changes to exposures
    $effect(() => {
        if ($viewMode === 'exposures') {
            loadExposures();
        }
    });

    // Also fetch on mount if already in exposures mode
    onMount(() => {
        if ($viewMode === 'exposures') {
            loadExposures();
        }
    });
</script>

<div class="h-full w-full overflow-auto bg-gray-50 relative">
    <!-- Floating Back to Canvas Button -->
    <div class="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20 pointer-events-auto">
        <div
            class="flex bg-white rounded-lg p-1 border border-gray-200/60 shadow-lg"
        >
            <button
                class="px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center gap-2"
                class:bg-primary-50={$viewMode === "conceptual"}
                class:text-primary-600={$viewMode === "conceptual"}
                class:shadow-sm={$viewMode === "conceptual"}
                class:text-gray-500={$viewMode !== "conceptual"}
                class:hover:text-gray-900={$viewMode !== "conceptual"}
                onclick={() => ($viewMode = "conceptual")}
                title="Conceptual View"
            >
                <Icon icon="octicon:workflow-16" class="w-3.5 h-3.5" />
                Conceptual
            </button>
            <button
                class="px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center gap-2"
                class:bg-primary-50={$viewMode === "logical"}
                class:text-primary-600={$viewMode === "logical"}
                class:shadow-sm={$viewMode === "logical"}
                class:text-gray-500={$viewMode !== "logical"}
                class:hover:text-gray-900={$viewMode !== "logical"}
                onclick={() => ($viewMode = "logical")}
                title="Logical View"
            >
                <Icon icon="lucide:database" class="w-3.5 h-3.5" />
                Logical
            </button>
        </div>
    </div>

    {#if loading}
        <div class="flex items-center justify-center h-full">
            <div class="text-center">
                <Icon icon="lucide:loader-2" class="w-8 h-8 animate-spin text-primary-600 mx-auto mb-2" />
                <p class="text-sm text-gray-600">Loading exposures...</p>
            </div>
        </div>
    {:else if error}
        <div class="flex items-center justify-center h-full">
            <div class="bg-white/90 backdrop-blur-sm p-8 rounded-xl border border-red-200 shadow-xl text-center max-w-md mx-4">
                <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Icon icon="lucide:alert-circle" class="w-8 h-8 text-red-500" />
                </div>
                <h3 class="text-xl font-bold text-slate-800 mb-2">Error Loading Exposures</h3>
                <p class="text-slate-600 mb-4">{error}</p>
            </div>
        </div>
    {:else if exposures.length === 0}
        <div class="flex items-center justify-center h-full">
            <div class="bg-white/90 backdrop-blur-sm p-8 rounded-xl border border-amber-200 shadow-xl text-center max-w-md mx-4">
                <div class="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Icon icon="mdi:file-document-outline" class="w-8 h-8 text-amber-600" />
                </div>
                <h3 class="text-xl font-bold text-slate-800 mb-2">No Exposures Found</h3>
                <p class="text-slate-600 mb-4">
                    Create an <code class="bg-amber-50 px-2 py-1 rounded text-sm">exposures.yml</code> file in your dbt project to define downstream usage of your data model.
                </p>
                <div class="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800 text-left mt-4">
                    <strong class="block mb-1">Example structure:</strong>
                    <pre class="text-[10px] overflow-x-auto"><code>exposures:
  - name: my_dashboard
    label: My Dashboard
    type: dashboard
    description: Main business dashboard
    owner:
      name: analytics-team
    depends_on:
      - ref('my_model')</code></pre>
                </div>
            </div>
        </div>
    {:else}
        <div class="p-6">
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div class="overflow-x-auto overflow-y-auto max-h-[calc(100vh-12rem)]">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0 z-10">
                            <tr>
                                <th
                                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 sticky left-0 z-20 border-r border-gray-200"
                                >
                                    Entity
                                </th>
                                {#each exposures as exposure}
                                    <th
                                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 min-w-[150px]"
                                        title={exposure.description || exposure.name}
                                    >
                                        <div class="flex items-center gap-2">
                                            <Icon
                                                icon={getExposureIcon(exposure.type)}
                                                class="w-4 h-4 text-gray-500"
                                            />
                                            <span>{exposure.label || exposure.name}</span>
                                        </div>
                                        {#if exposure.owner?.name}
                                            <div class="text-[10px] font-normal text-gray-500 mt-1">
                                                Owner: {exposure.owner.name}
                                            </div>
                                        {/if}
                                    </th>
                                {/each}
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {#each entities as entity}
                                <tr class="hover:bg-gray-50 transition-colors">
                                    <td
                                        class="px-4 py-3 text-sm font-medium text-gray-900 bg-white sticky left-0 z-10 border-r border-gray-200"
                                    >
                                        {entity.label}
                                    </td>
                                    {#each exposures as exposure}
                                        <td class="px-4 py-3 text-sm text-center">
                                            {#if entityUsage[entity.id]?.includes(exposure.name)}
                                                <span class="text-green-600 font-semibold">✓</span>
                                            {:else}
                                                <span class="text-gray-300">—</span>
                                            {/if}
                                        </td>
                                    {/each}
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    {/if}
</div>

