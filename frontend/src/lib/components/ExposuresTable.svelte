<script lang="ts">
    import { onMount } from 'svelte';
    import {
        nodes,
        viewMode,
        folderFilter,
        tagFilter,
        exposureTypeFilter,
        exposureOwnerFilter,
        exposureEntityFilter
    } from '$lib/stores';
    import { getExposures } from '$lib/api';
    import type { Exposure, EntityUsage, EntityData } from '$lib/types';
    import { normalizeTags } from '$lib/utils';
    import Icon from '@iconify/svelte';

interface Props {
    exposuresEnabled: boolean;
    exposuresDefaultLayout: 'dashboards-as-rows' | 'entities-as-rows';
}

let { exposuresEnabled = true, exposuresDefaultLayout = 'dashboards-as-rows' }: Props = $props();

let exposures = $state<Exposure[]>([]);
let entityUsage = $state<EntityUsage>({});
let loading = $state(true);
let error = $state<string | null>(null);
let autoFitExposureHeaders = $state(true);
let tableViewportWidth = $state(0);
let tableViewportEl = $state<HTMLDivElement | null>(null);
let isTransposed = $state(exposuresDefaultLayout === 'dashboards-as-rows');
let userHasToggledLayout = $state(false);
let stickyColumnWidth = $state(240); // Width of the sticky row-label column
let isResizing = $state(false);

// Sync isTransposed when exposuresDefaultLayout prop changes (unless user has manually toggled)
$effect(() => {
    if (!userHasToggledLayout) {
        const newValue = exposuresDefaultLayout === 'dashboards-as-rows';
        if (isTransposed !== newValue) {
            isTransposed = newValue;
        }
    }
});

    // Derive entities from nodes (filter out group nodes and apply filters)
    let entities = $derived(
        $nodes
            .filter((n) => n.type !== 'group')
            .map((n) => {
                const data = n.data as unknown as EntityData;
                return {
                    id: n.id,
                    label: (data?.label || '').trim() || 'Entity',
                    folder: data?.folder,
                    tags: normalizeTags(data?.tags),
                };
            })
            .filter((entity) => {
                // Filter by specific entity ID (from exposures button)
                if ($exposureEntityFilter !== null) {
                    if (entity.id !== $exposureEntityFilter) {
                        return false;
                    }
                }

                // Filter by folder
                if ($folderFilter.length > 0) {
                    const entityFolder = entity.folder;
                    if (!entityFolder || !$folderFilter.includes(entityFolder)) {
                        return false;
                    }
                }

                // Filter by tag
                if ($tagFilter.length > 0) {
                    const entityTags = entity.tags;
                    const hasMatch = $tagFilter.some((tag) =>
                        entityTags.includes(tag),
                    );
                    if (!hasMatch) {
                        return false;
                    }
                }

                return true;
            })
            .map((e) => ({ id: e.id, label: e.label }))
            .sort((a, b) => a.label.localeCompare(b.label))
    );

    // Filter exposures by metadata
    let filteredExposures = $derived(
        exposures.filter((exposure) => {
            // Filter by type
            if ($exposureTypeFilter.length > 0) {
                const exposureType = exposure.type?.toLowerCase() || '';
                if (!exposureType || !$exposureTypeFilter.includes(exposureType)) {
                    return false;
                }
            }

            // Filter by owner
            if ($exposureOwnerFilter.length > 0) {
                const ownerName = exposure.owner?.name || '';
                if (!ownerName || !$exposureOwnerFilter.includes(ownerName)) {
                    return false;
                }
            }

            return true;
        })
    );

    // Progressive header density (delays horizontal scroll for many dashboards)
    type HeaderMode = 'normal' | 'narrow' | 'angled';
    let headerMode = $derived.by<HeaderMode>(() => {
        if (!autoFitExposureHeaders) return 'normal';

        // Determine what's in the horizontal dimension (columns)
        const horizontalCount = isTransposed ? entities.length : filteredExposures.length;
        if (tableViewportWidth <= 0) {
            // Fallback when we can't measure container size yet (e.g., first paint)
            if (horizontalCount >= 40) return 'angled';
            if (horizontalCount >= 20) return 'narrow';
            return 'normal';
        }

        // Use measured width to decide when to compact headers.
        // Roughly subtract space for the sticky entity column + borders/padding.
        const available = Math.max(tableViewportWidth - stickyColumnWidth, 0);
        const fits = (minWidth: number) => (minWidth > 0 ? Math.floor(available / minWidth) : 0);

        const fitsNormal = fits(150);
        const fitsNarrow = fits(120);

        if (horizontalCount <= fitsNormal) return 'normal';
        if (horizontalCount <= fitsNarrow) return 'narrow';
        return 'angled'; // last resort before relying heavily on horizontal scroll
    });

    let thClass = $derived(() => {
        switch (headerMode) {
            case 'angled':
                return 'px-2 py-2 text-left text-[11px] font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 min-w-[96px] align-bottom';
            case 'narrow':
                return 'px-2 py-2 text-left text-[11px] font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 min-w-[120px]';
            default:
                return 'px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 min-w-[150px]';
        }
    });

    let iconClass = $derived(() => (headerMode === 'normal' ? 'w-4 h-4' : 'w-3.5 h-3.5'));

    // Get unique exposure types and owners for filter dropdowns
    let availableTypes = $derived(
        Array.from(new Set(exposures.map(e => e.type).filter(Boolean))).sort()
    );

    let availableOwners = $derived(
        Array.from(new Set(exposures.map(e => e.owner?.name).filter(Boolean))).sort()
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

    // Resize handle functions
    function startResize(e: MouseEvent) {
        e.preventDefault();
        isResizing = true;
        document.addEventListener('mousemove', handleResize);
        document.addEventListener('mouseup', stopResize);
    }

    function handleResize(e: MouseEvent) {
        if (!tableViewportEl) return;
        const tableRect = tableViewportEl.getBoundingClientRect();
        const newWidth = e.clientX - tableRect.left;
        // Constrain width to reasonable bounds (100px to 600px)
        stickyColumnWidth = Math.max(100, Math.min(600, newWidth));
    }

    function stopResize() {
        isResizing = false;
        document.removeEventListener('mousemove', handleResize);
        document.removeEventListener('mouseup', stopResize);
    }

    // Fetch data when view mode changes to exposures
    $effect(() => {
        if ($viewMode === 'exposures') {
            loadExposures();
        } else {
            // Clear entity filter when switching away from exposures view
            exposureEntityFilter.set(null);
        }
    });

    // Also fetch on mount if already in exposures mode
    onMount(() => {
        if ($viewMode === 'exposures') {
            loadExposures();
        }

        // Measure table viewport width to auto-fit columns based on screen size.
        if (typeof ResizeObserver !== 'undefined') {
            const ro = new ResizeObserver((entries) => {
                const entry = entries[0];
                if (!entry) return;
                tableViewportWidth = Math.round(entry.contentRect.width);
            });

            if (tableViewportEl) ro.observe(tableViewportEl);

            return () => {
                ro.disconnect();
            };
        }
    });
</script>

<div class="h-full w-full overflow-auto bg-gray-50">
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
            <!-- Filter Controls -->
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-4">
                <div class="flex flex-wrap items-center gap-4">
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:filter" class="w-4 h-4 text-gray-500" />
                        <span class="text-sm font-medium text-gray-700">Filters:</span>
                    </div>

                    <!-- Exposure Type Filter -->
                    <div class="flex items-center gap-2">
                        <label for="exposure-type-filter" class="text-xs text-gray-600">Type:</label>
                        <select
                            id="exposure-type-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                            onchange={(e) => {
                                const value = (e.target as HTMLSelectElement).value;
                                if (value) {
                                    if (!$exposureTypeFilter.includes(value)) {
                                        $exposureTypeFilter = [...$exposureTypeFilter, value];
                                    }
                                    (e.target as HTMLSelectElement).value = '';
                                }
                            }}
                        >
                            <option value="">Select type...</option>
                            {#each availableTypes as type}
                                {#if type && !$exposureTypeFilter.includes(type)}
                                    <option value={type}>{type}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each $exposureTypeFilter as type}
                            <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs">
                                {type}
                                <button
                                    onclick={() => {
                                        $exposureTypeFilter = $exposureTypeFilter.filter(t => t !== type);
                                    }}
                                    class="hover:text-primary-900"
                                >
                                    <Icon icon="lucide:x" class="w-3 h-3" />
                                </button>
                            </span>
                        {/each}
                    </div>

                    <!-- Exposure Owner Filter -->
                    <div class="flex items-center gap-2">
                        <label for="exposure-owner-filter" class="text-xs text-gray-600">Owner:</label>
                        <select
                            id="exposure-owner-filter"
                            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                            onchange={(e) => {
                                const value = (e.target as HTMLSelectElement).value;
                                if (value) {
                                    if (!$exposureOwnerFilter.includes(value)) {
                                        $exposureOwnerFilter = [...$exposureOwnerFilter, value];
                                    }
                                    (e.target as HTMLSelectElement).value = '';
                                }
                            }}
                        >
                            <option value="">Select owner...</option>
                            {#each availableOwners as owner}
                                {#if owner && !$exposureOwnerFilter.includes(owner)}
                                    <option value={owner}>{owner}</option>
                                {/if}
                            {/each}
                        </select>
                        {#each $exposureOwnerFilter as owner}
                            <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs">
                                {owner}
                                <button
                                    onclick={() => {
                                        $exposureOwnerFilter = $exposureOwnerFilter.filter(o => o !== owner);
                                    }}
                                    class="hover:text-primary-900"
                                >
                                    <Icon icon="lucide:x" class="w-3 h-3" />
                                </button>
                            </span>
                        {/each}
                    </div>

                    <!-- Entity Filter Badge -->
                    {#if $exposureEntityFilter !== null}
                        {#each entities.filter(e => e.id === $exposureEntityFilter) as entity}
                            <span class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs">
                                Entity: {entity.label}
                                <button
                                    onclick={() => {
                                        exposureEntityFilter.set(null);
                                    }}
                                    class="hover:text-primary-900"
                                >
                                    <Icon icon="lucide:x" class="w-3 h-3" />
                                </button>
                            </span>
                        {/each}
                    {/if}

                    <!-- Clear All Filters -->
                    {#if $exposureTypeFilter.length > 0 || $exposureOwnerFilter.length > 0 || $exposureEntityFilter !== null}
                        <button
                            onclick={() => {
                                $exposureTypeFilter = [];
                                $exposureOwnerFilter = [];
                                exposureEntityFilter.set(null);
                            }}
                            class="text-xs text-gray-600 hover:text-gray-800 underline"
                        >
                            Clear exposure filters
                        </button>
                    {/if}

                    <!-- Table Density -->
                    <div class="flex items-center gap-2 ml-auto">
                        <!-- Transpose Toggle -->
                        <button
                            onclick={() => {
                                isTransposed = !isTransposed;
                                userHasToggledLayout = true;
                            }}
                            class="px-3 py-1.5 text-xs rounded font-medium text-gray-600 bg-white border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-1.5"
                            title={isTransposed ? "Switch to entities as rows" : "Switch to dashboards as rows"}
                        >
                            <Icon icon="lucide:rotate-cw" class="w-3.5 h-3.5" />
                            {isTransposed ? "Entities as rows" : "Dashboards as rows"}
                        </button>

                        <label class="flex items-center gap-2 text-xs text-gray-600 select-none cursor-pointer">
                            <input
                                type="checkbox"
                                checked={autoFitExposureHeaders}
                                onchange={(e) => (autoFitExposureHeaders = (e.target as HTMLInputElement).checked)}
                                class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                            />
                            Auto-fit columns
                        </label>
                    </div>
                </div>

                <!-- Entity Filters Info -->
                {#if $folderFilter.length > 0 || $tagFilter.length > 0}
                    <div class="mt-3 pt-3 border-t border-gray-200">
                        <div class="flex items-center gap-2 text-xs text-gray-600">
                            <Icon icon="lucide:info" class="w-3 h-3" />
                            <span>Entity filters active:</span>
                            {#if $folderFilter.length > 0}
                                <span class="text-gray-700 font-medium">
                                    {$folderFilter.length} folder{$folderFilter.length === 1 ? '' : 's'}
                                </span>
                            {/if}
                            {#if $tagFilter.length > 0}
                                <span class="text-gray-700 font-medium">
                                    {#if $folderFilter.length > 0}, {/if}
                                    {$tagFilter.length} tag{$tagFilter.length === 1 ? '' : 's'}
                                </span>
                            {/if}
                        </div>
                    </div>
                {/if}
            </div>

            <div class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div bind:this={tableViewportEl} class="overflow-x-auto overflow-y-auto max-h-[calc(100vh-10rem)]">
                    <table class="min-w-full divide-y divide-gray-200">
                        {#if !isTransposed}
                            <!-- Normal layout: entities as rows, exposures as columns -->
                            <thead class="bg-gray-50 sticky top-0 z-10">
                                <tr>
                                    <th
                                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 sticky left-0 z-20 border-r border-gray-200 relative"
                                        style={`width: ${stickyColumnWidth}px; min-width: ${stickyColumnWidth}px; max-width: ${stickyColumnWidth}px;`}
                                    >
                                        <div class="flex items-center justify-between">
                                            <span>Entity</span>
                                            <button
                                                onmousedown={startResize}
                                                class="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary-500 hover:w-1.5 transition-all"
                                                title="Drag to resize column"
                                                type="button"
                                            />
                                        </div>
                                    </th>
                                    {#each filteredExposures as exposure}
                                        <th
                                            class={thClass}
                                            title={exposure.description || exposure.name}
                                        >
                                            {#if headerMode === 'angled'}
                                                <div class="h-20 flex items-end">
                                                    <div class="origin-bottom-right -rotate-45 whitespace-nowrap flex items-center gap-1.5">
                                                        <Icon
                                                            icon={getExposureIcon(exposure.type)}
                                                            class={`${iconClass} text-gray-500`}
                                                        />
                                                        <span>{exposure.label || exposure.name}</span>
                                                    </div>
                                                </div>
                                            {:else}
                                                <div class="flex items-center gap-2">
                                                    <Icon
                                                        icon={getExposureIcon(exposure.type)}
                                                        class={`${iconClass} text-gray-500`}
                                                    />
                                                    <span class={headerMode === 'narrow' ? 'truncate max-w-[9rem]' : ''}>
                                                        {exposure.label || exposure.name}
                                                    </span>
                                                </div>
                                            {/if}
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
                                {#if entities.length === 0}
                                    <tr>
                                        <td colspan={Math.max(filteredExposures.length, 1) + 1} class="px-4 py-8 text-center text-sm text-gray-500">
                                            No entities match the current filters.
                                        </td>
                                    </tr>
                                {:else if filteredExposures.length === 0}
                                    <tr>
                                        <td colspan="2" class="px-4 py-8 text-center text-sm text-gray-500">
                                            No exposures match the current filters.
                                        </td>
                                    </tr>
                                {:else}
                                    {#each entities as entity}
                                        <tr class="hover:bg-gray-50 transition-colors">
                                            <td
                                                class="px-4 py-3 text-sm font-medium text-gray-900 bg-white sticky left-0 z-10 border-r border-gray-200"
                                                style={`width: ${stickyColumnWidth}px; min-width: ${stickyColumnWidth}px; max-width: ${stickyColumnWidth}px;`}
                                            >
                                                <div class="truncate" title={entity.label}>{entity.label}</div>
                                            </td>
                                            {#each filteredExposures as exposure}
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
                                {/if}
                            </tbody>
                        {:else}
                            <!-- Transposed layout: exposures as rows, entities as columns -->
                            <thead class="bg-gray-50 sticky top-0 z-10">
                                <tr>
                                    <th
                                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 sticky left-0 z-20 border-r border-gray-200 relative"
                                        style={`width: ${stickyColumnWidth}px; min-width: ${stickyColumnWidth}px; max-width: ${stickyColumnWidth}px;`}
                                    >
                                        <div class="flex items-center justify-between">
                                            <span>Dashboard</span>
                                            <button
                                                onmousedown={startResize}
                                                class="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary-500 hover:w-1.5 transition-all"
                                                title="Drag to resize column"
                                                type="button"
                                            />
                                        </div>
                                    </th>
                                    {#each entities as entity}
                                        <th
                                            class={thClass}
                                            title={entity.label}
                                        >
                                            <span class={headerMode === 'narrow' ? 'truncate max-w-[9rem]' : ''}>
                                                {entity.label}
                                            </span>
                                        </th>
                                    {/each}
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                {#if filteredExposures.length === 0}
                                    <tr>
                                        <td colspan="2" class="px-4 py-8 text-center text-sm text-gray-500">
                                            No exposures match the current filters.
                                        </td>
                                    </tr>
                                {:else if entities.length === 0}
                                    <tr>
                                        <td colspan={Math.max(entities.length, 1) + 1} class="px-4 py-8 text-center text-sm text-gray-500">
                                            No entities match the current filters.
                                        </td>
                                    </tr>
                                {:else}
                                    {#each filteredExposures as exposure}
                                        <tr class="hover:bg-gray-50 transition-colors">
                                            <td
                                                class="px-4 py-3 text-sm font-medium text-gray-900 bg-white sticky left-0 z-10 border-r border-gray-200"
                                                style={`width: ${stickyColumnWidth}px; min-width: ${stickyColumnWidth}px; max-width: ${stickyColumnWidth}px;`}
                                            >
                                                <div>
                                                    <div class="flex items-center gap-2 truncate" title={exposure.label || exposure.name}>
                                                        <Icon
                                                            icon={getExposureIcon(exposure.type)}
                                                            class={`${iconClass} text-gray-500 flex-shrink-0`}
                                                        />
                                                        <span class="truncate">{exposure.label || exposure.name}</span>
                                                    </div>
                                                    {#if exposure.owner?.name}
                                                        <div class="text-[10px] font-normal text-gray-500 mt-1 truncate">
                                                            Owner: {exposure.owner.name}
                                                        </div>
                                                    {/if}
                                                </div>
                                            </td>
                                            {#each entities as entity}
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
                                {/if}
                            </tbody>
                        {/if}
                    </table>
                </div>
            </div>
        </div>
    {/if}
</div>

