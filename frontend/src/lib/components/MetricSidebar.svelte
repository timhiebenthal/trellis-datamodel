<script lang="ts">
    import Icon from "$lib/components/Icon.svelte";
    import type { MetricCatalogEntry, MetricEntry } from "$lib/types";
    import { groupCatalogByEntity, metricLabelFromName } from "$lib/utils/metric-edits";

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
    let collapsedGroups = $state<Record<string, boolean>>({});
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
    const entityGroups = $derived(groupCatalogByEntity(filteredCatalog, metrics));

    function isGroupCollapsed(key: string): boolean {
        if (normalizedSearch) return false;
        return Boolean(collapsedGroups[key]);
    }

    function toggleGroup(key: string) {
        collapsedGroups = {
            ...collapsedGroups,
            [key]: !collapsedGroups[key],
        };
    }

    function subtitle(metric: MetricEntry): string {
        if (metric.dataset_ref) return metric.dataset_ref;
        return "unbound";
    }

    function onDragStartMetric(event: DragEvent, metric: MetricEntry) {
        if (!event.dataTransfer) return;
        event.dataTransfer.setData(
            "application/metric-tree-item",
            JSON.stringify({ kind: "tree", metricId: metric.id }),
        );
        event.dataTransfer.effectAllowed = "linkMove";
    }

    function onDragStartCatalog(event: DragEvent, entry: MetricCatalogEntry) {
        if (!event.dataTransfer) return;
        event.dataTransfer.setData(
            "application/metric-tree-item",
            JSON.stringify({ kind: "catalog", entry }),
        );
        event.dataTransfer.effectAllowed = "copyLink";
    }
</script>

<aside
    class="flex h-full w-80 shrink-0 flex-col border-r border-slate-200 bg-white"
    aria-label="Metric catalog"
    data-testid="metric-sidebar"
>
    <div class="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
        <div class="flex min-w-0 items-center gap-2">
            <Icon icon="lucide:trending-up" class="h-4 w-4 shrink-0 text-primary-600" />
            <h3 class="truncate text-sm font-semibold text-slate-800">Metrics</h3>
            <span class="rounded-full bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-slate-600">
                {metrics.length}
            </span>
        </div>

        {#if onaddmetric}
            <button
                type="button"
                class="inline-flex shrink-0 items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
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
                class="w-full rounded-md border border-slate-200 bg-slate-50/60 py-1.5 pl-8 pr-2.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-primary-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-primary-500"
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
                                class="group flex items-center gap-1 rounded-md border px-2 py-1.5 transition-colors cursor-grab active:cursor-grabbing"
                                class:border-primary-300={selectedMetricId === metric.id}
                                class:bg-primary-50={selectedMetricId === metric.id}
                                class:border-slate-200={selectedMetricId !== metric.id}
                                class:hover:border-slate-300={selectedMetricId !== metric.id}
                                draggable="true"
                                role="listitem"
                                ondragstart={(event) => onDragStartMetric(event, metric)}
                                data-testid="metric-sidebar-entry"
                            >
                                <button
                                    type="button"
                                    class="min-w-0 flex-1 text-left"
                                    onclick={() => onselectmetric?.(metric.id)}
                                    data-testid="metric-sidebar-select"
                                    title={metric.description || metric.label}
                                >
                                    <span class="flex items-center gap-1.5">
                                        <span
                                            class="h-2 w-2 shrink-0 rounded-full {metric.binding ? 'bg-primary-500' : 'bg-amber-500'}"
                                            aria-hidden="true"
                                        ></span>
                                        <span class="truncate text-sm font-medium text-slate-800">
                                            {metric.label}
                                        </span>
                                    </span>
                                    {#if metric.binding}
                                        <span class="mt-0.5 flex items-center gap-1 truncate pl-3.5 text-[11px] font-medium text-primary-600">
                                            <Icon icon="lucide:link" class="h-3 w-3 shrink-0" />
                                            <span class="sr-only">bound · </span>
                                            <span class="truncate font-mono">{metric.binding.dataset}.{metric.binding.name}</span>
                                        </span>
                                    {:else}
                                        <span class="mt-0.5 block truncate pl-3.5 text-[11px] font-mono text-slate-500">
                                            {subtitle(metric)}
                                        </span>
                                    {/if}
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
                <div class="mt-2 space-y-1">
                    {#each entityGroups as group (group.key)}
                        {@const collapsed = isGroupCollapsed(group.key)}
                        <div data-testid="metric-sidebar-entity-group" data-group-key={group.key}>
                            <button
                                type="button"
                                class="flex w-full cursor-pointer select-none items-center gap-1.5 rounded-md px-2 py-1 text-left text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-100"
                                onclick={() => toggleGroup(group.key)}
                                aria-expanded={!collapsed}
                                data-testid="metric-sidebar-entity-group-toggle"
                            >
                                <span
                                    class="flex h-3 w-3 shrink-0 items-center justify-center transition-transform {collapsed ? '-rotate-90' : 'rotate-0'}"
                                >
                                    <Icon icon="lucide:chevron-down" class="h-3 w-3 text-slate-400" />
                                </span>
                                <Icon
                                    icon={group.isCrossDataset ? "lucide:layers" : "lucide:database"}
                                    class="h-3.5 w-3.5 shrink-0 text-slate-400"
                                />
                                <span class="min-w-0 flex-1 truncate">{group.label}</span>
                                <span class="rounded-full bg-slate-100 px-1.5 py-0.2 text-[10px] font-medium tabular-nums text-slate-500">
                                    {group.items.length}
                                </span>
                            </button>

                            {#if !collapsed}
                                <ul class="ml-[13px] mt-0.5 space-y-0.5 border-l border-slate-200 pl-2">
                                    {#each group.items as item (`${item.entry.dataset ?? ''}::${item.entry.name}`)}
                                        {#if item.status === "available"}
                                            <li>
                                                <button
                                                    type="button"
                                                    draggable="true"
                                                    ondragstart={(event) => onDragStartCatalog(event, item.entry)}
                                                    class="group flex w-full cursor-grab items-center justify-between gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-left text-xs font-medium text-slate-700 transition-all hover:border-primary-500 hover:bg-primary-50/40 active:cursor-grabbing"
                                                    onclick={() => onaddcatalogmetric?.(item.entry)}
                                                    data-testid="metric-sidebar-catalog-add"
                                                    title="Click to add {item.entry.name}, or drag onto a metric's + Add driver / + Add effect button"
                                                >
                                                    <span class="min-w-0 flex-1 truncate">{item.entry.name}</span>
                                                    <Icon
                                                        icon="lucide:plus"
                                                        class="h-3.5 w-3.5 shrink-0 text-slate-400 transition-colors group-hover:text-primary-600"
                                                    />
                                                </button>
                                            </li>
                                        {:else if item.status === "added"}
                                            {@const isSelected = Boolean(item.boundMetricId && selectedMetricId === item.boundMetricId)}
                                            <li>
                                                <div
                                                    class="flex w-full cursor-pointer items-center justify-between gap-1.5 rounded-md border px-2 py-1 text-left text-xs font-medium transition-colors"
                                                    class:border-primary-400={isSelected}
                                                    class:bg-primary-100={isSelected}
                                                    class:text-primary-900={isSelected}
                                                    class:border-primary-200={!isSelected}
                                                    class:bg-primary-50={!isSelected}
                                                    class:text-primary-700={!isSelected}
                                                    class:hover:border-primary-300={!isSelected}
                                                    role="button"
                                                    tabindex="0"
                                                    onclick={() => item.boundMetricId && onselectmetric?.(item.boundMetricId)}
                                                    onkeydown={(e) => {
                                                        if ((e.key === "Enter" || e.key === " ") && item.boundMetricId) {
                                                            e.preventDefault();
                                                            onselectmetric?.(item.boundMetricId);
                                                        }
                                                    }}
                                                    title="Already on this tree — click to select"
                                                    data-testid="metric-sidebar-catalog-added"
                                                >
                                                    <span class="min-w-0 flex-1 truncate">{item.entry.name}</span>
                                                    <Icon icon="lucide:check" class="h-3.5 w-3.5 shrink-0 text-primary-600" />
                                                </div>
                                            </li>
                                        {:else}
                                            <li
                                                class="flex items-center justify-between gap-1.5 rounded-md border border-transparent px-2 py-1 text-xs text-slate-400"
                                                title={item.entry.reason ?? "This metric cannot be bound to a dataset"}
                                                data-readonly="true"
                                                data-testid="metric-sidebar-catalog-readonly"
                                            >
                                                <span class="min-w-0 flex-1 truncate">{item.entry.name}</span>
                                                <Icon icon="lucide:lock" class="h-3.5 w-3.5 shrink-0 text-slate-300" />
                                            </li>
                                        {/if}
                                    {/each}
                                </ul>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}

            <p class="mt-3 px-1 text-[11px] leading-relaxed text-slate-400">
                Adding a metric from here stores a reference. The definition stays in the
                semantic model and is never copied.
            </p>
        </section>
    </div>
</aside>
