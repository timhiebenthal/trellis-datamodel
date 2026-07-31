<script lang="ts">
    import { getBusMatrix } from '$lib/api';
    import { onMount } from 'svelte';
    import Icon from '@iconify/svelte';
    import * as XLSX from 'xlsx';

    interface Dimension {
        id: string;
        label: string;
        tags?: string[];
        dbt_model?: string;
    }

    interface Fact {
        id: string;
        label: string;
        tags?: string[];
        dbt_model?: string;
    }

    interface Connection {
        dimension_id: string;
        fact_id: string;
    }

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
    let buildStatusFilter = $state<string[]>([]);

    // Sort options: 'label-asc' | 'count-desc'
    let dimensionSort = $state<string>('label-asc');
    let factSort = $state<string>('label-asc');

    function getEntityLabel(entity: Dimension | Fact): string {
        return entity.label || entity.id;
    }

    function hasConnection(dimensionId: string, factId: string): boolean {
        return connectionLookup.has(`${dimensionId}-${factId}`);
    }

    function matchesBuildStatus(entity: Dimension | Fact): boolean {
        if (buildStatusFilter.length === 0) return true;
        const status = entity.dbt_model ? 'bound' : 'unbound';
        return buildStatusFilter.includes(status);
    }

    // Filtered (unsorted) collections — counts depend on these
    let filteredDimensions = $derived(
        dimensions.filter(dimension => {
            if (dimensionFilter.length > 0 && !dimensionFilter.includes(dimension.id)) return false;
            if (tagFilter.length > 0) {
                const tags = dimension.tags || [];
                if (!tagFilter.some(tag => tags.includes(tag))) return false;
            }
            if (!matchesBuildStatus(dimension)) return false;
            return true;
        })
    );

    let filteredFacts = $derived(
        facts.filter(fact => {
            if (factFilter.length > 0 && !factFilter.includes(fact.id)) return false;
            if (tagFilter.length > 0) {
                const tags = fact.tags || [];
                if (!tagFilter.some(tag => tags.includes(tag))) return false;
            }
            if (!matchesBuildStatus(fact)) return false;
            return true;
        })
    );

    // Count how many visible filtered facts each filtered dimension connects to
    let dimensionVisibleFactCounts = $derived(
        (() => {
            const map = new Map<string, number>();
            for (const dim of filteredDimensions) {
                let count = 0;
                for (const fact of filteredFacts) {
                    if (connectionLookup.has(`${dim.id}-${fact.id}`)) count++;
                }
                map.set(dim.id, count);
            }
            return map;
        })()
    );

    // Count how many visible filtered dimensions each filtered fact connects to
    let factVisibleDimensionCounts = $derived(
        (() => {
            const map = new Map<string, number>();
            for (const fact of filteredFacts) {
                let count = 0;
                for (const dim of filteredDimensions) {
                    if (connectionLookup.has(`${dim.id}-${fact.id}`)) count++;
                }
                map.set(fact.id, count);
            }
            return map;
        })()
    );

    // Sorted collections based on sort state
    let sortedDimensions = $derived(
        [...filteredDimensions].sort((a, b) => {
            if (dimensionSort === 'count-desc') {
                const countA = dimensionVisibleFactCounts.get(a.id) ?? 0;
                const countB = dimensionVisibleFactCounts.get(b.id) ?? 0;
                if (countB !== countA) return countB - countA;
            }
            return getEntityLabel(a).localeCompare(getEntityLabel(b));
        })
    );

    let sortedFacts = $derived(
        [...filteredFacts].sort((a, b) => {
            if (factSort === 'count-desc') {
                const countA = factVisibleDimensionCounts.get(a.id) ?? 0;
                const countB = factVisibleDimensionCounts.get(b.id) ?? 0;
                if (countB !== countA) return countB - countA;
            }
            return getEntityLabel(a).localeCompare(getEntityLabel(b));
        })
    );

    // All unique tags from dimensions and facts
    let availableTags = $derived(
        Array.from(new Set([
            ...dimensions.flatMap(d => d.tags || []),
            ...facts.flatMap(f => f.tags || [])
        ])).sort()
    );

    function exportFullMatrix() {
        // Always use the full unfiltered data regardless of active UI filters
        const allDimensions = [...dimensions].sort((a, b) =>
            getEntityLabel(a).localeCompare(getEntityLabel(b))
        );
        const allFacts = [...facts].sort((a, b) =>
            getEntityLabel(a).localeCompare(getEntityLabel(b))
        );

        const fullLookup = new Map<string, boolean>();
        connections.forEach(conn => {
            fullLookup.set(`${conn.dimension_id}-${conn.fact_id}`, true);
        });

        // Matrix sheet: header row + one row per dimension
        const matrixRows: string[][] = [
            ['', ...allFacts.map(f => getEntityLabel(f))]
        ];
        for (const dim of allDimensions) {
            const row = [getEntityLabel(dim)];
            for (const fact of allFacts) {
                row.push(fullLookup.has(`${dim.id}-${fact.id}`) ? 'x' : '');
            }
            matrixRows.push(row);
        }

        // Longlist sheet: every dimension-fact combination
        const longlistRows: { dimension: string; fact: string; linked: string }[] = [];
        for (const dim of allDimensions) {
            for (const fact of allFacts) {
                longlistRows.push({
                    dimension: getEntityLabel(dim),
                    fact: getEntityLabel(fact),
                    linked: fullLookup.has(`${dim.id}-${fact.id}`) ? 'TRUE' : 'FALSE',
                });
            }
        }

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(matrixRows), 'Matrix');
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(longlistRows), 'Longlist');
        XLSX.writeFile(wb, 'trellis-bus-matrix.xlsx');
    }

    onMount(async () => {
        try {
            loading = true;
            error = null;

            const data = await getBusMatrix();

            dimensions = data.dimensions || [];
            facts = data.facts || [];
            connections = data.connections || [];

            const lookup = new Map<string, boolean>();
            connections.forEach(conn => {
                lookup.set(`${conn.dimension_id}-${conn.fact_id}`, true);
            });
            connectionLookup = lookup;

        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load Bus Matrix data';
        } finally {
            loading = false;
        }
    });
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
                <div class="flex items-start justify-between gap-4">
                    <div>
                        <h2 class="text-xl font-bold text-gray-800">Bus Matrix</h2>
                        <p class="text-sm text-gray-600 mt-1">View which business processes (facts) use the same dimensions.<br>This can help you with prioritization, but also with integrating and aligning definitions across departments, allowing you to use a `Conformed Dimension` across use cases.</p>
                    </div>
                    <button
                        onclick={exportFullMatrix}
                        disabled={dimensions.length === 0 || facts.length === 0}
                        class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                    >
                        <Icon icon="lucide:download" class="w-4 h-4" />
                        Export full matrix
                    </button>
                </div>
            </div>

            <!-- Filter and Sort Controls -->
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-4 overflow-x-auto">
                <div class="flex items-center gap-3 min-w-0">
                    <Icon icon="lucide:filter" class="w-4 h-4 text-gray-500 shrink-0" />

                    <!-- Dimension Filter -->
                    <div class="flex items-center gap-1.5 shrink-0">
                        <label for="dimension-filter" class="text-xs text-gray-600">Dimensions:</label>
                        <select
                            id="dimension-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 w-28"
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
                            <option value="">Add...</option>
                            {#each dimensions as dimension}
                                {#if !dimensionFilter.includes(dimension.id)}
                                    <option value={dimension.id}>{dimension.label}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each dimensionFilter as dimId}
                            {#each dimensions.filter(d => d.id === dimId) as dimension}
                                <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs shrink-0">
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
                    <div class="flex items-center gap-1.5 shrink-0">
                        <label for="fact-filter" class="text-xs text-gray-600">Facts:</label>
                        <select
                            id="fact-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 w-28"
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
                            <option value="">Add...</option>
                            {#each facts as fact}
                                {#if !factFilter.includes(fact.id)}
                                    <option value={fact.id}>{fact.label}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each factFilter as factId}
                            {#each facts.filter(f => f.id === factId) as fact}
                                <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs shrink-0">
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
                    <div class="flex items-center gap-1.5 shrink-0">
                        <label for="tag-filter" class="text-xs text-gray-600">Tags:</label>
                        <select
                            id="tag-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 w-28"
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
                            <option value="">Add...</option>
                            {#each availableTags as tag}
                                {#if !tagFilter.includes(tag)}
                                    <option value={tag}>{tag}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each tagFilter as tag}
                            <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs shrink-0">
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

                    <!-- Build Status Filter -->
                    <div class="flex items-center gap-1.5 shrink-0">
                        <label for="build-status-filter" class="text-xs text-gray-600">Built:</label>
                        <select
                            id="build-status-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 w-28"
                            onchange={(e) => {
                                const value = (e.target as HTMLSelectElement).value;
                                if (value) {
                                    if (!buildStatusFilter.includes(value)) {
                                        buildStatusFilter = [...buildStatusFilter, value];
                                    }
                                    (e.target as HTMLSelectElement).value = '';
                                }
                            }}
                        >
                            <option value="">Add...</option>
                            {#if !buildStatusFilter.includes('bound')}
                                <option value="bound">Bound</option>
                            {/if}
                            {#if !buildStatusFilter.includes('unbound')}
                                <option value="unbound">Unbound</option>
                            {/if}
                        </select>
                        {#each buildStatusFilter as status}
                            <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs shrink-0">
                                {status === 'bound' ? 'Bound' : 'Unbound'}
                                <button
                                    onclick={() => {
                                        buildStatusFilter = buildStatusFilter.filter(s => s !== status);
                                    }}
                                    class="hover:text-primary-900"
                                >
                                    <Icon icon="lucide:x" class="w-3 h-3" />
                                </button>
                            </span>
                        {/each}
                    </div>

                    <!-- Clear All Filters -->
                    {#if dimensionFilter.length > 0 || factFilter.length > 0 || tagFilter.length > 0 || buildStatusFilter.length > 0}
                        <button
                            onclick={() => {
                                dimensionFilter = [];
                                factFilter = [];
                                tagFilter = [];
                                buildStatusFilter = [];
                            }}
                            class="text-xs text-gray-600 hover:text-gray-800 underline shrink-0"
                        >
                            Clear all
                        </button>
                    {/if}

                    <!-- Divider -->
                    <div class="w-px h-4 bg-gray-200 ml-auto shrink-0"></div>

                    <!-- Sort Controls -->
                    <div class="flex items-center gap-3 shrink-0">
                        <Icon icon="lucide:arrow-up-down" class="w-4 h-4 text-gray-500 shrink-0" />
                        <div class="flex items-center gap-1.5">
                            <label for="dimension-sort" class="text-xs text-gray-600">Dimensions:</label>
                            <select
                                id="dimension-sort"
                                aria-label="Sort dimensions"
                                bind:value={dimensionSort}
                                class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 w-36"
                            >
                                <option value="label-asc">Label A–Z</option>
                                <option value="count-desc">Usage count ↓</option>
                            </select>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label for="fact-sort" class="text-xs text-gray-600">Facts:</label>
                            <select
                                id="fact-sort"
                                aria-label="Sort facts"
                                bind:value={factSort}
                                class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 w-36"
                            >
                                <option value="label-asc">Label A–Z</option>
                                <option value="count-desc">Usage count ↓</option>
                            </select>
                        </div>
                    </div>
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
                                {#each sortedFacts as fact}
                                    <th class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 min-w-[150px]">
                                        <div class="flex items-center gap-2">
                                            <Icon icon="lucide:bar-chart-3" class="w-4 h-4 text-blue-600" />
                                            <span
                                                class="flex-shrink-0 inline-block w-2 h-2 rounded-full {fact.dbt_model ? 'bg-primary-600' : 'border border-gray-300'}"
                                                title={fact.dbt_model ? `Built with dbt: ${fact.dbt_model.split('.').pop()}` : 'Not yet built with dbt'}
                                            ></span>
                                            <span class="truncate">{fact.label}</span>
                                            {#if factVisibleDimensionCounts.get(fact.id) !== undefined}
                                                <span
                                                    aria-label="{factVisibleDimensionCounts.get(fact.id)} connected dimensions"
                                                    class="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-700"
                                                >
                                                    {factVisibleDimensionCounts.get(fact.id)}
                                                </span>
                                            {/if}
                                        </div>
                                    </th>
                                {/each}
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {#if sortedDimensions.length === 0}
                                <tr>
                                    <td colspan={sortedFacts.length + 1} class="px-4 py-8 text-center text-sm text-gray-500">
                                        No dimensions match the current filters.
                                    </td>
                                </tr>
                            {:else if sortedFacts.length === 0}
                                <tr>
                                    <td colspan="2" class="px-4 py-8 text-center text-sm text-gray-500">
                                        No facts match the current filters.
                                    </td>
                                </tr>
                            {:else}
                                {#each sortedDimensions as dimension}
                                    <tr class="hover:bg-gray-50 transition-colors">
                                        <td class="px-4 py-3 text-sm font-medium text-gray-900 bg-white sticky left-0 z-10 border-r border-gray-200 w-[200px] min-w-[200px]">
                                            <div class="flex items-center gap-2" title={dimension.label}>
                                                <Icon icon="lucide:list" class="w-4 h-4 text-green-600 flex-shrink-0" />
                                                <span
                                                    class="flex-shrink-0 inline-block w-2 h-2 rounded-full {dimension.dbt_model ? 'bg-primary-600' : 'border border-gray-300'}"
                                                    title={dimension.dbt_model ? `Built with dbt: ${dimension.dbt_model.split('.').pop()}` : 'Not yet built with dbt'}
                                                ></span>
                                                <span class="truncate">{dimension.label}</span>
                                                <span
                                                    aria-label="{dimensionVisibleFactCounts.get(dimension.id) ?? 0} connected facts"
                                                    class="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 text-xs font-semibold rounded-full bg-green-100 text-green-700 flex-shrink-0"
                                                >
                                                    {dimensionVisibleFactCounts.get(dimension.id) ?? 0}
                                                </span>
                                            </div>
                                        </td>
                                        {#each sortedFacts as fact}
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
