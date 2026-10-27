<script lang="ts">
    import Icon from "$lib/components/Icon.svelte";
    import type { MetricCatalogEntry, MetricEntry } from "$lib/types";
    import { groupCatalog, metricLabelFromName } from "$lib/utils/metric-edits";

    /**
     * The catalog. Everything the sidebar shows comes from
     * `metric_tree.yml` (already on the tree) or `semantic_model.yml` (bindable
     * or read-only), so a metric is never invented here.
     */
    let {
        metrics = [],
        catalog = [],
        selectedMetricId = null,
        onaddmetric,
        onaddcatalogmetric,
        onselectmetric,
        ondeletemetric,
    }: {
        metrics?: MetricEntry[];
        catalog?: MetricCatalogEntry[];
        selectedMetricId?: string | null;
        onaddmetric?: () => void;
        onaddcatalogmetric?: (entry: MetricCatalogEntry) => void;
        onselectmetric?: (metricId: string) => void;
        ondeletemetric?: (metricId: string) => void;
    } = $props();

    let searchTerm = $state("");
    const normalizedSearch = $derived(searchTerm.trim().toLowerCase());

    function matchesMetric(metric: MetricEntry, query: string): boolean {
        if (!query) return true;
        return [
            metric.label,
            metric.id,
            metric.dataset_ref,
            metric.binding?.dataset,
            metric.binding?.name,
            metric.description,
        ].some((field) => field?.toLowerCase().includes(query));
    }

    function matchesCatalogEntry(entry: MetricCatalogEntry, query: string): boolean {
        if (!query) return true;
        return [
            entry.name,
            metricLabelFromName(entry.name),
            entry.dataset,
            entry.entity_id,
        ].some((field) => field?.toLowerCase().includes(query));
    }

    const filteredMetrics = $derived(
        metrics.filter((metric) => matchesMetric(metric, normalizedSearch)),
    );
    const filteredCatalog = $derived(
        catalog.filter((entry) => matchesCatalogEntry(entry, normalizedSearch)),
    );
    const groups = $derived(groupCatalog(filteredCatalog, metrics));

    function subtitle(metric: MetricEntry): string {
        if (metric.binding) return `bound · ${metric.binding.dataset}`;
        if (metric.dataset_ref) return metric.dataset_ref;
        return "unbound";
    }
</script>

<aside
    class="flex h-full w-80 shrink-0 flex-col border-r border-slate-200 bg-white"
    aria-label="Metric catalog"
    data-testid="metric-sidebar"
>
    <div class="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
        <div class="flex min-w-0 items-center gap-2">
            <Icon icon="lucide:trending-up" class="h-4 w-4 shrink-0 text-violet-600" />
            <h3 class="truncate text-sm font-semibold text-slate-800">Metrics</h3>
            <span class="rounded-full bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-slate-600">
                {metrics.length}
            </span>
        </div>

        {#if onaddmetric}
            <button
                type="button"
                class="inline-flex shrink-0 items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 transition-colors hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700"
                onclick={onaddmetric}
                data-testid="metric-sidebar-add"
            >
                <Icon icon="lucide:plus" class="h-3.5 w-3.5" />
                Add metric
            </button>
        {/if}
    </div>

    <div class="border-b border-slate-200 px-3 py-2.5">
        <div class="relative">
            <Icon
                icon="lucide:search"
                class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
            />
            <input
                type="search"
                placeholder="Search metrics..."
                aria-label="Search metrics"
                bind:value={searchTerm}
                class="w-full rounded-md border border-slate-200 bg-slate-50/60 py-1.5 pl-8 pr-2.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-violet-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-violet-400"
                data-testid="metric-sidebar-search"
            />
        </div>
    </div>

    <div class="flex-1 overflow-y-auto">
        <section class="px-3 py-3" data-testid="metric-sidebar-tree">
            <h4 class="px-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                On this tree
            </h4>

            {#if metrics.length === 0}
                <p class="mt-2 px-1 text-xs leading-relaxed text-slate-500">
                    Nothing yet. Add a metric by hand, or bind one from the semantic model below.
                </p>
            {:else if filteredMetrics.length === 0}
                <p class="mt-2 px-1 text-xs italic leading-relaxed text-slate-400">
                    No matching metrics on this tree.
                </p>
            {:else}
                <ul class="mt-2 space-y-1">
                    {#each filteredMetrics as metric (metric.id)}
                        <li>
                            <div
                                class="group flex items-center gap-1 rounded-md border px-2 py-1.5 transition-colors"
                                class:border-violet-300={selectedMetricId === metric.id}
                                class:bg-violet-50={selectedMetricId === metric.id}
                                class:border-slate-200={selectedMetricId !== metric.id}
                                class:hover:border-slate-300={selectedMetricId !== metric.id}
                                data-testid="metric-sidebar-entry"
                            >
                                <button
                                    type="button"
                                    class="min-w-0 flex-1 text-left"
                                    onclick={() => onselectmetric?.(metric.id)}
                                    data-testid="metric-sidebar-select"
                                    title={metric.description || metric.label}
                                >
                                    <span class="block truncate text-sm font-medium text-slate-800">
                                        {metric.label}
                                    </span>
                                    <span class="block truncate text-[11px] text-slate-500">
                                        {subtitle(metric)}
                                    </span>
                                </button>

                                {#if ondeletemetric}
                                    <button
                                        type="button"
                                        class="shrink-0 rounded p-1 text-slate-300 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                                        title="Remove {metric.label} from the tree"
                                        aria-label="Remove {metric.label} from the tree"
                                        onclick={() => ondeletemetric?.(metric.id)}
                                        data-testid="metric-sidebar-delete"
                                    >
                                        <Icon icon="lucide:trash-2" class="h-3.5 w-3.5" />
                                    </button>
                                {/if}
                            </div>
                        </li>
                    {/each}
                </ul>
            {/if}
        </section>

        <section class="border-t border-slate-200 px-3 py-3" data-testid="metric-sidebar-catalog">
            <h4 class="px-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                From the semantic model
            </h4>

            {#if catalog.length === 0}
                <p class="mt-2 px-1 text-xs leading-relaxed text-slate-500">
                    No metrics found in the semantic model yet.
                </p>
            {:else if filteredCatalog.length === 0}
                <p class="mt-2 px-1 text-xs italic leading-relaxed text-slate-400">
                    No matching metrics in the semantic model.
                </p>
            {:else}
                {#if groups.available.length > 0}
                    <ul class="mt-2 space-y-1">
                        {#each groups.available as entry (entry.name)}
                            <li>
                                <button
                                    type="button"
                                    class="flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left transition-colors hover:border-violet-200 hover:bg-violet-50"
                                    onclick={() => onaddcatalogmetric?.(entry)}
                                    data-testid="metric-sidebar-catalog-add"
                                    title="Add {entry.name} as a reference to {entry.dataset}"
                                >
                                    <Icon icon="lucide:plus" class="h-3.5 w-3.5 shrink-0 text-violet-500" />
                                    <span class="min-w-0 flex-1">
                                        <span class="block truncate text-sm text-slate-700">{entry.name}</span>
                                        <span class="block truncate text-[11px] text-slate-400">{entry.dataset}</span>
                                    </span>
                                </button>
                            </li>
                        {/each}
                    </ul>
                {/if}

                {#if groups.added.length > 0}
                    <ul class="mt-2 space-y-0.5">
                        {#each groups.added as entry (entry.name)}
                            <li
                                class="flex items-center gap-2 px-2 py-1 text-xs text-slate-400"
                                title="Already on this tree"
                                data-testid="metric-sidebar-catalog-added"
                            >
                                <Icon icon="lucide:check" class="h-3.5 w-3.5 shrink-0 text-violet-400" />
                                <span class="truncate line-through">{entry.name}</span>
                            </li>
                        {/each}
                    </ul>
                {/if}

                {#if groups.unavailable.length > 0}
                    <ul class="mt-2 space-y-0.5">
                        {#each groups.unavailable as entry (entry.name)}
                            <li
                                class="flex items-center gap-2 rounded-md px-2 py-1 text-xs text-slate-400"
                                title={entry.reason ?? "This metric cannot be bound to a dataset"}
                                data-readonly="true"
                                data-testid="metric-sidebar-catalog-readonly"
                            >
                                <Icon icon="lucide:lock" class="h-3.5 w-3.5 shrink-0 text-slate-300" />
                                <span class="truncate">{entry.name}</span>
                            </li>
                        {/each}
                    </ul>
                {/if}
            {/if}

            <p class="mt-3 px-1 text-[11px] leading-relaxed text-slate-400">
                Adding a metric from here stores a reference. The definition stays in the
                semantic model and is never copied.
            </p>
        </section>
    </div>
</aside>
