<script lang="ts">
    import { getBusMatrix } from '$lib/api';
    import { onMount } from 'svelte';
    import Icon from '@iconify/svelte';

    // Performance Optimization Notes for Large Datasets:
    // 1. Debounce filter inputs (to be added in Wave 2): Use a 300ms debounce delay
    //    to avoid re-rendering the matrix on every keystroke.
    // 2. Virtual scrolling: Consider implementing for 100+ dimensions/facts.
    //    Libraries like svelte-virtual-list or tanstack-virtual can render only visible rows.
    // 3. Memoization: Use $: to memoize connection checks and reduce recalculations.
    // 4. Web Workers: Offload relationship building to web worker for 1000+ entities.
    //
    // Target: Render Bus Matrix within 1 second for 100 dimensions × 50 facts.

    let dimensions = $state<Dimension[]>([]);
    let facts = $state<Fact[]>([]);
    let connections = $state<Connection[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let connectionLookup = $state<Map<string, boolean>>(new Map());

    // Filters
    let dimensionFilter = $state<string[]>([]);
    let factFilter = $state<string[]>([]);
    let tagFilter = $state<string[]>([]);

    interface Dimension {
        id: string;
        label: string;
        tags?: string[];
    }

    interface Fact {
        id: string;
        label: string;
        tags?: string[];
    }

    interface Connection {
        dimension_id: string;
        fact_id: string;
    }

    // Filter dimensions based on filters
    let filteredDimensions = $derived(
        dimensions.filter(dimension => {
            // Filter by dimension selection
            if (dimensionFilter.length > 0 && !dimensionFilter.includes(dimension.id)) {
                return false;
            }

            // Filter by tags
            if (tagFilter.length > 0) {
                const dimensionTags = dimension.tags || [];
                const hasMatch = tagFilter.some(tag => dimensionTags.includes(tag));
                if (!hasMatch) {
                    return false;
                }
            }

            return true;
        })
    );

    // Filter facts based on filters
    let filteredFacts = $derived(
        facts.filter(fact => {
            // Filter by fact selection
            if (factFilter.length > 0 && !factFilter.includes(fact.id)) {
                return false;
            }

            // Filter by tags
            if (tagFilter.length > 0) {
                const factTags = fact.tags || [];
                const hasMatch = tagFilter.some(tag => factTags.includes(tag));
                if (!hasMatch) {
                    return false;
                }
            }

            return true;
        })
    );

    // Get all unique tags from dimensions and facts
    let availableTags = $derived(
        Array.from(new Set([
            ...dimensions.flatMap(d => d.tags || []),
            ...facts.flatMap(f => f.tags || [])
        ])).sort()
    );

    onMount(async () => {
        try {
            loading = true;
            error = null;

            // Fetch Bus Matrix data from API
            console.log("Bus Matrix: Starting API fetch...");
            const data = await getBusMatrix();

            console.log("Bus Matrix: API response received - dimensions:", data.dimensions?.length, "facts:", data.facts?.length, "connections:", data.connections?.length);

            dimensions = data.dimensions || [];
            facts = data.facts || [];
            connections = data.connections || [];

            console.log("Bus Matrix: Data assigned - dimensions:", dimensions.length, "facts:", facts.length, "connections:", connections.length);

            // Create a Map for fast lookup of connections
            connectionLookup = new Map();
            connections.forEach(conn => {
                const key = `${conn.dimension_id}-${conn.fact_id}`;
                connectionLookup.set(key, true);
            });

            console.log("Bus Matrix: Connection lookup map created with", connectionLookup.size, "entries");
            console.log("Bus Matrix: Sample connection keys:", Array.from(connectionLookup.keys()).slice(0, 5));

        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load Bus Matrix data';
            console.error("Bus Matrix: Error loading data:", error);
        } finally {
            loading = false;
        }
    });

    function hasConnection(dimensionId: string, factId: string): boolean {
        const key = `${dimensionId}-${factId}`;
        const result = connectionLookup.has(key);
        console.log("Bus Matrix: Checking connection - dimension:", dimensionId, "fact:", factId, "result:", result);
        return result;
    }
</script>

<div class="h-full w-full overflow-auto bg-gray-50">
    {#if loading}
        <div class="flex items-center justify-center h-full">
            <div class="text-center">
                <div class="w-8 h-8 animate-spin border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-2"></div>
                <p class="text-sm text-gray-600">Loading Bus Matrix...</p>
            </div>
        </div>
    {:else if error}
        <div class="flex items-center justify-center h-full">
            <div class="bg-white/90 backdrop-blur-sm p-8 rounded-xl border border-red-200 shadow-xl text-center max-w-md mx-4">
                <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <h3 class="text-xl font-bold text-slate-800 mb-2">Error Loading Bus Matrix</h3>
                <p class="text-slate-600 mb-4">{error}</p>
            </div>
        </div>
    {:else}
        <div class="p-6">
            <!-- Header -->
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-4">
                <div>
                    <h2 class="text-xl font-bold text-gray-800">Bus Matrix</h2>
                    <p class="text-sm text-gray-600 mt-1">View which business processes (facts) use the same dimensions.<br>This can help you with prioritization, but also with integrating and aligning definitions across departments, allowing you to use a `Conformed Dimension` across use cases.</p>
                </div>
            </div>

            <!-- Filter Controls -->
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-4">
                <div class="flex flex-wrap items-center gap-4">
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:filter" class="w-4 h-4 text-gray-500" />
                        <span class="text-sm font-medium text-gray-700">Filters:</span>
                    </div>

                    <!-- Dimension Filter -->
                    <div class="flex items-center gap-2">
                        <label for="dimension-filter" class="text-xs text-gray-600">Dimensions:</label>
                        <select
                            id="dimension-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                            onchange={(e) => {
                                const value = (e.target as HTMLSelectElement).value;
                                if (value) {
                                    if (!dimensionFilter.includes(value)) {
                                        dimensionFilter = [...dimensionFilter, value];
                                    }
                                    (e.target as HTMLSelectElement).value = '';
                                }
                            }}
                        >
                            <option value="">Select dimension...</option>
                            {#each dimensions as dimension}
                                {#if !dimensionFilter.includes(dimension.id)}
                                    <option value={dimension.id}>{dimension.label}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each dimensionFilter as dimId}
                            {#each dimensions.filter(d => d.id === dimId) as dimension}
                                <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs">
                                    {dimension.label}
                                    <button
                                        onclick={() => {
                                            dimensionFilter = dimensionFilter.filter(id => id !== dimId);
                                        }}
                                        class="hover:text-primary-900"
                                    >
                                        <Icon icon="lucide:x" class="w-3 h-3" />
                                    </button>
                                </span>
                            {/each}
                        {/each}
                    </div>

                    <!-- Fact Filter -->
                    <div class="flex items-center gap-2">
                        <label for="fact-filter" class="text-xs text-gray-600">Facts:</label>
                        <select
                            id="fact-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                            onchange={(e) => {
                                const value = (e.target as HTMLSelectElement).value;
                                if (value) {
                                    if (!factFilter.includes(value)) {
                                        factFilter = [...factFilter, value];
                                    }
                                    (e.target as HTMLSelectElement).value = '';
                                }
                            }}
                        >
                            <option value="">Select fact...</option>
                            {#each facts as fact}
                                {#if !factFilter.includes(fact.id)}
                                    <option value={fact.id}>{fact.label}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each factFilter as factId}
                            {#each facts.filter(f => f.id === factId) as fact}
                                <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs">
                                    {fact.label}
                                    <button
                                        onclick={() => {
                                            factFilter = factFilter.filter(id => id !== factId);
                                        }}
                                        class="hover:text-primary-900"
                                    >
                                        <Icon icon="lucide:x" class="w-3 h-3" />
                                    </button>
                                </span>
                            {/each}
                        {/each}
                    </div>

                    <!-- Tag Filter -->
                    <div class="flex items-center gap-2">
                        <label for="tag-filter" class="text-xs text-gray-600">Tags:</label>
                        <select
                            id="tag-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                            onchange={(e) => {
                                const value = (e.target as HTMLSelectElement).value;
                                if (value) {
                                    if (!tagFilter.includes(value)) {
                                        tagFilter = [...tagFilter, value];
                                    }
                                    (e.target as HTMLSelectElement).value = '';
                                }
                            }}
                        >
                            <option value="">Select tag...</option>
                            {#each availableTags as tag}
                                {#if !tagFilter.includes(tag)}
                                    <option value={tag}>{tag}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each tagFilter as tag}
                            <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs">
                                {tag}
                                <button
                                    onclick={() => {
                                        tagFilter = tagFilter.filter(t => t !== tag);
                                    }}
                                    class="hover:text-primary-900"
                                >
                                    <Icon icon="lucide:x" class="w-3 h-3" />
                                </button>
                            </span>
                        {/each}
                    </div>

                    <!-- Clear All Filters -->
                    {#if dimensionFilter.length > 0 || factFilter.length > 0 || tagFilter.length > 0}
                        <button
                            onclick={() => {
                                dimensionFilter = [];
                                factFilter = [];
                                tagFilter = [];
                            }}
                            class="text-xs text-gray-600 hover:text-gray-800 underline"
                        >
                            Clear all filters
                        </button>
                    {/if}
                </div>
            </div>

            <!-- Table -->
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div class="overflow-x-auto overflow-y-auto max-h-[calc(100vh-14rem)]">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0 z-10">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 sticky left-0 z-20 border-r border-gray-200 w-[200px] min-w-[200px]">
                                    <div class="flex items-center gap-2">
                                        <Icon icon="lucide:list" class="w-4 h-4 text-green-600" />
                                        <span>Dimensions</span>
                                    </div>
                                </th>
                                {#each filteredFacts as fact}
                                    <th class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 min-w-[150px]">
                                        <div class="flex items-center gap-2">
                                            <Icon icon="lucide:bar-chart-3" class="w-4 h-4 text-blue-600" />
                                            <span class="truncate">{fact.label}</span>
                                        </div>
                                    </th>
                                {/each}
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {#if filteredDimensions.length === 0}
                                <tr>
                                    <td colspan={filteredFacts.length + 1} class="px-4 py-8 text-center text-sm text-gray-500">
                                        No dimensions match the current filters.
                                    </td>
                                </tr>
                            {:else if filteredFacts.length === 0}
                                <tr>
                                    <td colspan="2" class="px-4 py-8 text-center text-sm text-gray-500">
                                        No facts match the current filters.
                                    </td>
                                </tr>
                            {:else}
                                {#each filteredDimensions as dimension}
                                    <tr class="hover:bg-gray-50 transition-colors">
                                        <td class="px-4 py-3 text-sm font-medium text-gray-900 bg-white sticky left-0 z-10 border-r border-gray-200 w-[200px] min-w-[200px]">
                                            <div class="flex items-center gap-2" title={dimension.label}>
                                                <Icon icon="lucide:list" class="w-4 h-4 text-green-600 flex-shrink-0" />
                                                <span class="truncate">{dimension.label}</span>
                                            </div>
                                        </td>
                                        {#each filteredFacts as fact}
                                            <td class="px-4 py-3 text-sm text-center">
                                                {#if hasConnection(dimension.id, fact.id)}
                                                    <span class="text-green-600 font-semibold">✓</span>
                                                {:else}
                                                    <span class="text-gray-300">—</span>
                                                {/if}
                                            </td>
                                        {/each}
                                    </tr>
                                {/each}
                            {/if}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    /* Performance note: For datasets with 100+ dimensions/facts, consider implementing
     * virtual scrolling (e.g., using svelte-virtual-list or tanstack-virtual)
     * to render only visible rows/columns. This can significantly improve performance
     * for large matrices by reducing DOM nodes from O(n×m) to O(visible).
     * Current implementation uses sticky positioning which works well for moderate sizes. */
</style>

