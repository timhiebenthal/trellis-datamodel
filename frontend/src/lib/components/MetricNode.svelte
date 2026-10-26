<script lang="ts">
    import { Handle, Position, type NodeProps } from "@xyflow/svelte";
    import { getContext } from "svelte";
    import Icon from "$lib/components/Icon.svelte";
    import type { MetricCanvasActions } from "$lib/utils/metric-graph";
    import type { MetricEntry, MetricNodeData } from "$lib/types";

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
</script>

<div
    class="group relative w-[248px] rounded-lg border bg-white shadow-sm transition-all hover:shadow-md"
    class:border-violet-200={!selected}
    class:border-violet-500={selected}
    class:ring-2={selected}
    class:ring-violet-200={selected}
    class:opacity-90={isUnresolved && !selected}
    data-testid="metric-node"
    data-metric-id={metric?.id}
    title={metric?.description || label}
>
    <!-- Direction rail: drivers arrive on the left handle, effects leave on the right -->
    <span class="absolute inset-y-0 left-0 w-1 rounded-l-lg bg-violet-400" aria-hidden="true"></span>

    <Handle
        type="target"
        position={Position.Left}
        class="!h-2.5 !w-2.5 !rounded-full !border-2 !border-white !bg-violet-500"
        title="Influenced by another metric"
    />
    <Handle
        type="source"
        position={Position.Right}
        class="!h-2.5 !w-2.5 !rounded-full !border-2 !border-white !bg-violet-500"
        title="Drag to the metric this one influences"
    />

    <div class="py-2.5 pl-4 pr-2">
        <div class="flex items-start gap-1.5">
            <Icon icon="lucide:trending-up" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-600" />
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
                    class="inline-flex max-w-full items-center gap-1 truncate rounded border border-violet-200 bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-700"
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
