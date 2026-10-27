<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";
    import { getContext } from "svelte";
    import Icon from "$lib/components/Icon.svelte";
    import { groupCatalog, metricLabelFromName } from "$lib/utils/metric-edits";
    import type { MetricCanvasActions, MetricRelationKind } from "$lib/utils/metric-graph";
    import type { MetricCatalogEntry, MetricEntry, MetricNodeData } from "$lib/types";

    let { data, selected }: NodeProps = $props();

    // The node renders directly out of the payload rather than a copy, so a save
    // response that flips `unresolved` reaches the canvas without a remount.
    const nodeData = $derived(data as unknown as MetricNodeData);
    const metric = $derived<MetricEntry | undefined>(nodeData?.metric);
    const binding = $derived(metric?.binding ?? null);
    const dataset = $derived(binding?.dataset ?? metric?.dataset_ref ?? null);
    const expression = $derived((metric?.expression ?? "").trim());
    const isUnresolved = $derived(nodeData?.unresolved === true || metric?.unresolved === true);
    const label = $derived(metric?.label || metric?.id || "Untitled metric");

    const unresolvedHint = $derived(
        binding
            ? `The semantic model no longer defines ${binding.dataset}.${binding.name}. The reference is kept.`
            : dataset
              ? `The dataset "${dataset}" no longer resolves to an entity in the data model.`
              : "This metric no longer resolves to anything Trellis can read.",
    );

    const actions = getContext<MetricCanvasActions | undefined>("metricCanvas");

    let openPicker = $state<MetricRelationKind | null>(null);
    let pickerSearch = $state("");
    let dragOverRelation = $state<MetricRelationKind | null>(null);
    let searchInput = $state<HTMLInputElement | null>(null);

    const hasRelationActions = $derived(
        Boolean(
            actions?.addRelatedDraft ||
                actions?.addRelatedCatalogMetric ||
                actions?.connectRelatedMetric,
        ),
    );

    const allMetrics = $derived(actions?.getMetrics?.() ?? []);
    const allCatalog = $derived(actions?.getCatalog?.() ?? []);
    const allInfluences = $derived(actions?.getInfluences?.() ?? []);

    function isAlreadyLinked(relation: MetricRelationKind, otherId: string): boolean {
        if (!metric?.id || otherId === metric.id) return true;
        if (relation === "driver") {
            return allInfluences.some(
                (inf) => inf.effect === metric.id && inf.drivers.includes(otherId),
            );
        }
        return allInfluences.some(
            (inf) => inf.effect === otherId && inf.drivers.includes(metric.id),
        );
    }

    const normalizedQuery = $derived(pickerSearch.trim().toLowerCase());

    const linkableTreeMetrics = $derived(
        openPicker
            ? allMetrics.filter((entry) => {
                  if (isAlreadyLinked(openPicker!, entry.id)) return false;
                  if (!normalizedQuery) return true;
                  return [
                      entry.label,
                      entry.id,
                      entry.dataset_ref,
                      entry.binding?.dataset,
                      entry.binding?.name,
                  ].some((field) => field?.toLowerCase().includes(normalizedQuery));
              })
            : [],
    );

    const availableCatalogEntries = $derived(
        openPicker
            ? groupCatalog(allCatalog, allMetrics).available.filter((entry) => {
                  if (!normalizedQuery) return true;
                  return [
                      entry.name,
                      metricLabelFromName(entry.name),
                      entry.dataset,
                      entry.entity_id,
                  ].some((field) => field?.toLowerCase().includes(normalizedQuery));
              })
            : [],
    );

    function togglePicker(relation: MetricRelationKind, event: MouseEvent) {
        event.stopPropagation();
        if (openPicker === relation) {
            openPicker = null;
            pickerSearch = "";
            return;
        }
        openPicker = relation;
        pickerSearch = "";
        queueMicrotask(() => searchInput?.focus());
    }

    function closePicker() {
        openPicker = null;
        pickerSearch = "";
    }

    function handlePickDraft(relation: MetricRelationKind, event: MouseEvent) {
        event.stopPropagation();
        if (!metric?.id) return;
        actions?.addRelatedDraft?.(metric.id, relation);
        closePicker();
    }

    function handlePickTreeMetric(
        relation: MetricRelationKind,
        targetId: string,
        event: MouseEvent,
    ) {
        event.stopPropagation();
        if (!metric?.id) return;
        actions?.connectRelatedMetric?.(metric.id, relation, targetId);
        closePicker();
    }

    function handlePickCatalogMetric(
        relation: MetricRelationKind,
        entry: MetricCatalogEntry,
        event: MouseEvent,
    ) {
        event.stopPropagation();
        if (!metric?.id) return;
        actions?.addRelatedCatalogMetric?.(metric.id, relation, entry);
        closePicker();
    }

    function handleDragOver(relation: MetricRelationKind, event: DragEvent) {
        if (!event.dataTransfer?.types.includes("application/metric-tree-item")) return;
        event.preventDefault();
        event.stopPropagation();
        dragOverRelation = relation;
    }

    function handleDragLeave(relation: MetricRelationKind) {
        if (dragOverRelation === relation) {
            dragOverRelation = null;
        }
    }

    function handleDrop(relation: MetricRelationKind, event: DragEvent) {
        dragOverRelation = null;
        const raw = event.dataTransfer?.getData("application/metric-tree-item");
        if (!raw || !metric?.id) return;
        event.preventDefault();
        event.stopPropagation();

        try {
            const parsed = JSON.parse(raw) as
                | { kind: "tree"; metricId: string }
                | { kind: "catalog"; entry: MetricCatalogEntry };
            if (parsed.kind === "tree" && parsed.metricId) {
                actions?.connectRelatedMetric?.(metric.id, relation, parsed.metricId);
                closePicker();
            } else if (parsed.kind === "catalog" && parsed.entry) {
                actions?.addRelatedCatalogMetric?.(metric.id, relation, parsed.entry);
                closePicker();
            }
        } catch {
            // Ignore malformed drag payload.
        }
    }
</script>

<div
    class="group relative w-[248px] rounded-lg border bg-white shadow-sm transition-all hover:shadow-md"
    class:border-slate-200={!selected}
    class:border-primary-600={selected}
    class:ring-2={selected}
    class:ring-primary-200={selected}
    class:opacity-90={isUnresolved && !selected}
    data-testid="metric-node"
    data-metric-id={metric?.id}
    title={metric?.description || label}
>
    <!-- Accent rail -->
    <span class="absolute inset-y-0 left-0 w-1 rounded-l-lg bg-primary-500" aria-hidden="true"></span>

    <Handle
        type="target"
        position={Position.Top}
        class="!h-3.5 !w-3.5 !rounded-full !border-2 !border-white !bg-primary-600"
        title="Connect from the upper metric this one drives"
    />
    <Handle
        type="source"
        position={Position.Bottom}
        class="!h-3.5 !w-3.5 !rounded-full !border-2 !border-white !bg-primary-600"
        title="Drag to a driver metric below"
    />

    {#if hasRelationActions}
        <!-- Top action: + Add effect (metric above that this metric drives) -->
        <div
            class="nodrag nopan absolute left-1/2 top-0 z-20 -translate-x-1/2 -translate-y-1/2"
            role="group"
            ondragover={(event) => handleDragOver("effect", event)}
            ondragleave={() => handleDragLeave("effect")}
            ondrop={(event) => handleDrop("effect", event)}
        >
            <button
                type="button"
                class="group/btn inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-semibold shadow-sm transition-all"
                class:border-primary-600={openPicker === "effect" || dragOverRelation === "effect"}
                class:bg-primary-600={openPicker === "effect" || dragOverRelation === "effect"}
                class:text-white={openPicker === "effect" || dragOverRelation === "effect"}
                class:border-primary-300={openPicker !== "effect" && dragOverRelation !== "effect"}
                class:bg-white={openPicker !== "effect" && dragOverRelation !== "effect"}
                class:text-primary-700={openPicker !== "effect" && dragOverRelation !== "effect"}
                class:hover:border-primary-600={openPicker !== "effect"}
                class:hover:bg-primary-600={openPicker !== "effect"}
                class:hover:text-white={openPicker !== "effect"}
                onclick={(event) => togglePicker("effect", event)}
                title="Add or drop an effect metric above {label}"
                aria-label="Add effect above {label}"
                data-testid="metric-node-add-effect"
            >
                <Icon icon="lucide:plus" class="h-3 w-3 shrink-0" />
                <span
                    class="overflow-hidden whitespace-nowrap transition-all duration-150"
                    class:max-w-[72px]={openPicker === "effect" || dragOverRelation === "effect" || selected}
                    class:max-w-0={openPicker !== "effect" && dragOverRelation !== "effect" && !selected}
                    class:group-hover:max-w-[72px]={true}
                >
                    Add effect
                </span>
            </button>
        </div>

        <!-- Bottom action: + Add driver (input metric below that drives this metric) -->
        <div
            class="nodrag nopan absolute bottom-0 left-1/2 z-20 -translate-x-1/2 translate-y-1/2"
            role="group"
            ondragover={(event) => handleDragOver("driver", event)}
            ondragleave={() => handleDragLeave("driver")}
            ondrop={(event) => handleDrop("driver", event)}
        >
            <button
                type="button"
                class="group/btn inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-semibold shadow-sm transition-all"
                class:border-primary-600={openPicker === "driver" || dragOverRelation === "driver"}
                class:bg-primary-600={openPicker === "driver" || dragOverRelation === "driver"}
                class:text-white={openPicker === "driver" || dragOverRelation === "driver"}
                class:border-primary-300={openPicker !== "driver" && dragOverRelation !== "driver"}
                class:bg-white={openPicker !== "driver" && dragOverRelation !== "driver"}
                class:text-primary-700={openPicker !== "driver" && dragOverRelation !== "driver"}
                class:hover:border-primary-600={openPicker !== "driver"}
                class:hover:bg-primary-600={openPicker !== "driver"}
                class:hover:text-white={openPicker !== "driver"}
                onclick={(event) => togglePicker("driver", event)}
                title="Add or drop a driver metric below {label}"
                aria-label="Add driver below {label}"
                data-testid="metric-node-add-driver"
            >
                <Icon icon="lucide:plus" class="h-3 w-3 shrink-0" />
                <span
                    class="overflow-hidden whitespace-nowrap transition-all duration-150"
                    class:max-w-[72px]={openPicker === "driver" || dragOverRelation === "driver" || selected}
                    class:max-w-0={openPicker !== "driver" && dragOverRelation !== "driver" && !selected}
                    class:group-hover:max-w-[72px]={true}
                >
                    Add driver
                </span>
            </button>
        </div>

        {#if openPicker}
            {@const relation = openPicker}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="nodrag nopan nowheel absolute left-1/2 z-30 w-64 -translate-x-1/2 rounded-xl border border-slate-200 bg-white p-2.5 shadow-xl"
                class:bottom-full={relation === "effect"}
                class:mb-3={relation === "effect"}
                class:top-full={relation === "driver"}
                class:mt-3={relation === "driver"}
                onclick={(event) => event.stopPropagation()}
                ondragover={(event) => handleDragOver(relation, event)}
                ondragleave={() => handleDragLeave(relation)}
                ondrop={(event) => handleDrop(relation, event)}
                data-testid="metric-node-picker"
                data-relation={relation}
            >
                <div class="mb-2 flex items-center justify-between gap-2">
                    <span class="text-[11px] font-semibold uppercase tracking-wide text-primary-700">
                        {relation === "driver"
                            ? `Add driver below ${label}`
                            : `Add effect above ${label}`}
                    </span>
                    <button
                        type="button"
                        class="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        aria-label="Close picker"
                        onclick={(event) => {
                            event.stopPropagation();
                            closePicker();
                        }}
                    >
                        <Icon icon="lucide:x" class="h-3.5 w-3.5" />
                    </button>
                </div>

                <div class="relative mb-2">
                    <Icon
                        icon="lucide:search"
                        class="pointer-events-none absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-slate-400"
                    />
                    <input
                        bind:this={searchInput}
                        type="search"
                        placeholder="Search or drop metric here..."
                        bind:value={pickerSearch}
                        onkeydown={(event) => {
                            if (event.key === "Escape") closePicker();
                        }}
                        class="w-full rounded-md border border-slate-200 bg-slate-50 py-1 pl-6 pr-2 text-xs text-slate-800 placeholder:text-slate-400 focus:border-primary-500 focus:bg-white focus:outline-none"
                        data-testid="metric-node-picker-search"
                    />
                </div>

                <div class="max-h-44 space-y-2 overflow-y-auto pr-0.5">
                    {#if actions?.addRelatedDraft}
                        <button
                            type="button"
                            class="flex w-full items-center gap-1.5 rounded-md border border-dashed border-primary-300 bg-primary-50/60 px-2 py-1.5 text-left text-xs font-medium text-primary-700 transition-colors hover:bg-primary-100"
                            onclick={(event) => handlePickDraft(relation, event)}
                            data-testid="metric-node-picker-draft"
                        >
                            <Icon icon="lucide:plus" class="h-3.5 w-3.5 shrink-0" />
                            <span>New draft {relation}</span>
                        </button>
                    {/if}

                    {#if linkableTreeMetrics.length > 0}
                        <div>
                            <p class="px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                On this tree
                            </p>
                            <ul class="mt-1 space-y-0.5">
                                {#each linkableTreeMetrics as entry (entry.id)}
                                    <li>
                                        <button
                                            type="button"
                                            class="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1 text-left text-xs text-slate-700 hover:bg-primary-50 hover:text-primary-800"
                                            onclick={(event) =>
                                                handlePickTreeMetric(relation, entry.id, event)}
                                            data-testid="metric-node-picker-tree-item"
                                        >
                                            <span class="truncate font-medium">{entry.label}</span>
                                            <span class="shrink-0 text-[10px] text-slate-400">link</span>
                                        </button>
                                    </li>
                                {/each}
                            </ul>
                        </div>
                    {/if}

                    {#if availableCatalogEntries.length > 0}
                        <div>
                            <p class="px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                From semantic model
                            </p>
                            <ul class="mt-1 space-y-0.5">
                                {#each availableCatalogEntries as entry (entry.name)}
                                    <li>
                                        <button
                                            type="button"
                                            class="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1 text-left text-xs text-slate-700 hover:bg-primary-50 hover:text-primary-800"
                                            onclick={(event) =>
                                                handlePickCatalogMetric(relation, entry, event)}
                                            data-testid="metric-node-picker-catalog-item"
                                        >
                                            <span class="min-w-0 flex-1 truncate">{entry.name}</span>
                                            <span class="shrink-0 text-[10px] text-slate-400">
                                                {entry.dataset}
                                            </span>
                                        </button>
                                    </li>
                                {/each}
                            </ul>
                        </div>
                    {/if}

                    {#if linkableTreeMetrics.length === 0 && availableCatalogEntries.length === 0}
                        <p class="px-1 py-1 text-[11px] italic text-slate-400">
                            No matching metrics found.
                        </p>
                    {/if}
                </div>
            </div>
        {/if}
    {/if}

    <div class="py-2.5 pl-4 pr-2">
        <div class="flex items-start gap-1.5">
            <Icon icon="lucide:trending-up" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary-600" />
            <p class="min-w-0 flex-1 text-sm font-semibold leading-snug break-words text-slate-800">
                {label}
            </p>
            {#if actions?.deleteMetric}
                <button
                    type="button"
                    class="nodrag nopan -mt-0.5 rounded p-1 text-slate-300 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                    title="Remove {label} from the tree"
                    aria-label="Remove {label} from the tree"
                    data-testid="metric-node-delete"
                    onclick={(event) => {
                        event.stopPropagation();
                        actions?.deleteMetric?.(metric?.id ?? "");
                    }}
                >
                    <Icon icon="lucide:trash-2" class="h-3.5 w-3.5" />
                </button>
            {/if}
        </div>

        {#if expression}
            <p class="mt-1 truncate font-mono text-[10px] leading-relaxed text-slate-400" title={expression}>
                {expression}
            </p>
        {/if}

        <div class="mt-2 flex flex-wrap items-center gap-1">
            {#if binding}
                <span
                    class="inline-flex max-w-full items-center gap-1 truncate rounded border border-primary-200 bg-primary-50 px-1.5 py-0.5 text-[10px] font-medium text-primary-700"
                    title="Bound: read from {binding.dataset}.{binding.name} in the semantic model"
                    data-testid="metric-node-bound"
                >
                    <Icon icon="lucide:link-2" class="h-3 w-3 shrink-0" />
                    <span class="truncate">bound &middot; {binding.dataset}</span>
                </span>
            {:else if dataset}
                <span
                    class="inline-flex max-w-full items-center gap-1 truncate rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600"
                    title="Draft: dataset_ref points at {dataset}"
                    data-testid="metric-node-dataset"
                >
                    <Icon icon="lucide:database" class="h-3 w-3 shrink-0" />
                    <span class="truncate">{dataset}</span>
                </span>
            {:else}
                <span
                    class="inline-flex items-center gap-1 rounded border border-dashed border-slate-300 px-1.5 py-0.5 text-[10px] font-medium text-slate-500"
                    title="No dataset bound - this metric is drafted by hand"
                    data-testid="metric-node-unbound"
                >
                    unbound
                </span>
            {/if}

            {#if isUnresolved}
                <span
                    class="inline-flex items-center gap-1 rounded border border-amber-300 bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800"
                    title={unresolvedHint}
                    data-testid="metric-node-unresolved"
                >
                    <Icon icon="lucide:triangle-alert" class="h-3 w-3 shrink-0" />
                    unresolved
                </span>
            {/if}
        </div>
    </div>
</div>

<style>
    :global(.svelte-flow__node:has([data-testid="metric-node-picker"])) {
        z-index: 1001 !important;
    }
</style>
