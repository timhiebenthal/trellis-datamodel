<script lang="ts">
    import Icon from "$lib/components/Icon.svelte";
    import type { MetricEntry } from "$lib/types";

    /**
     * The inspector for one metric. Drafts are editable; a bound metric shows the
     * reference it holds plus the definition's expression, read-only, because the
     * definition stays in `semantic_model.yml` - copying it into this file is
     * exactly what the metric tree is designed not to do.
     */
    let {
        metric = null,
        datasets = [],
        focus = null,
        warnings = [],
        error = null,
        isSaving = false,
        hasUnsavedChanges = false,
        incompleteIds = [],
        onchange,
        onunlink,
        onclose,
    }: {
        metric?: MetricEntry | null;
        datasets?: string[];
        focus?: "label" | null;
        warnings?: string[];
        error?: string | null;
        isSaving?: boolean;
        hasUnsavedChanges?: boolean;
        incompleteIds?: string[];
        onchange?: (patch: Partial<MetricEntry>) => void;
        onunlink?: (metricId: string) => void;
        onclose?: () => void;
    } = $props();

    let labelInput = $state<HTMLInputElement | null>(null);
    let datasetDropdownRef = $state<HTMLDivElement | null>(null);
    let datasetDropdownOpen = $state(false);
    let datasetFilterActive = $state(false);
    let activeDatasetIndex = $state(-1);

    const binding = $derived(metric?.binding ?? null);
    const needsExpression = $derived(
        !!metric && !binding && !(metric.expression ?? "").trim(),
    );
    const filteredDatasets = $derived.by(() => {
        const query = (metric?.dataset_ref ?? "").trim().toLowerCase();
        if (!datasetFilterActive || !query) return datasets;
        return datasets.filter((id) => id.toLowerCase().includes(query));
    });

    // `focus === 'label'` is how "Add metric" lands the caret in the name field.
    $effect(() => {
        if (focus === "label" && labelInput) {
            labelInput.focus();
            labelInput.select();
        }
    });

    $effect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (datasetDropdownRef && !datasetDropdownRef.contains(event.target as Node)) {
                datasetDropdownOpen = false;
                datasetFilterActive = false;
            }
        }

        if (datasetDropdownOpen) {
            document.addEventListener("click", handleClickOutside);
        }

        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    });

    function openDatasetDropdown() {
        if (datasets.length === 0) return;
        datasetDropdownOpen = true;
        datasetFilterActive = false;
        activeDatasetIndex = -1;
    }

    function toggleDatasetDropdown() {
        if (datasetDropdownOpen) {
            datasetDropdownOpen = false;
            datasetFilterActive = false;
        } else {
            openDatasetDropdown();
        }
    }

    function selectDataset(dataset: string) {
        onchange?.({ dataset_ref: dataset });
        datasetDropdownOpen = false;
        datasetFilterActive = false;
        activeDatasetIndex = -1;
    }

    function handleDatasetKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            if (datasetDropdownOpen) {
                datasetDropdownOpen = false;
                datasetFilterActive = false;
                event.preventDefault();
            }
        } else if (event.key === "ArrowDown") {
            if (!datasetDropdownOpen && datasets.length > 0) {
                openDatasetDropdown();
            }
            if (filteredDatasets.length > 0) {
                event.preventDefault();
                activeDatasetIndex = Math.min(activeDatasetIndex + 1, filteredDatasets.length - 1);
            }
        } else if (event.key === "ArrowUp") {
            if (datasetDropdownOpen && filteredDatasets.length > 0) {
                event.preventDefault();
                activeDatasetIndex = Math.max(activeDatasetIndex - 1, 0);
            }
        } else if (event.key === "Enter") {
            if (
                datasetDropdownOpen &&
                activeDatasetIndex >= 0 &&
                activeDatasetIndex < filteredDatasets.length
            ) {
                event.preventDefault();
                selectDataset(filteredDatasets[activeDatasetIndex]);
            }
        }
    }

    const fieldClass =
        "w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-sm text-slate-800 outline-none transition-colors focus:border-primary-500 focus:ring-1 focus:ring-primary-500 disabled:bg-slate-50 disabled:text-slate-500";
    const labelClass =
        "mb-1 flex items-baseline justify-between gap-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400";
</script>

<aside
    class="flex max-h-full w-80 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
    aria-label="Metric details"
    data-testid="metric-detail-panel"
>
    {#if !metric}
        <div class="flex flex-1 flex-col items-center justify-center gap-2 px-6 py-10 text-center">
            <div class="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100">
                <Icon icon="lucide:mouse-pointer-2" class="h-5 w-5 text-slate-400" />
            </div>
            <p class="text-sm font-medium text-slate-600">Select a metric</p>
            <p class="text-xs leading-relaxed text-slate-500">
                Pick a node or a row in the sidebar to see what it is and edit a draft.
            </p>
        </div>
    {:else}
        <header class="flex items-start gap-2 border-b border-slate-200 px-4 py-3">
            <Icon
                icon={binding ? "lucide:link" : "lucide:trending-up"}
                class="mt-0.5 h-4 w-4 shrink-0 text-primary-600"
            />
            <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold text-slate-800" title={metric.label}>
                    {metric.label}
                </p>
                <p class="mt-0.5 truncate text-[11px] text-slate-500">
                    {#if binding}
                        bound reference
                    {:else}
                        draft
                        {#if metric.dataset_ref}&middot; {metric.dataset_ref}{/if}
                    {/if}
                </p>
            </div>
            {#if onclose}
                <button
                    type="button"
                    class="shrink-0 rounded p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                    aria-label="Close details"
                    title="Close details"
                    onclick={onclose}
                    data-testid="metric-detail-close"
                >
                    <Icon icon="lucide:x" class="h-3.5 w-3.5" />
                </button>
            {/if}
        </header>

        <div class="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {#if binding}
                <div class="rounded-lg border border-primary-200 bg-primary-50/60 px-3 py-2.5">
                    <p class="text-[11px] font-semibold uppercase tracking-wide text-primary-700">
                        Definition
                    </p>
                    <p class="mt-1 font-mono text-xs break-all text-primary-900">
                        {binding.dataset}.{binding.name}
                    </p>
                    {#if metric.resolved_expression}
                        <pre
                            class="mt-2 overflow-x-auto rounded-md border border-primary-200 bg-white px-2 py-1.5 font-mono text-[11px] leading-relaxed text-primary-900"
                            data-testid="metric-resolved-expression">{metric.resolved_expression}</pre
                        >
                        <p class="mt-1.5 text-[11px] leading-relaxed text-primary-800/80">
                            Read from the semantic model. Edit it there; Trellis stores the reference,
                            never a copy.
                        </p>
                    {:else}
                        <p class="mt-1.5 text-[11px] leading-relaxed text-primary-800/80">
                            Read from the semantic model. Trellis stores the reference, never a copy,
                            so this file cannot drift from the definition.
                        </p>
                    {/if}
                </div>

                {#if onunlink}
                    <button
                        type="button"
                        class="inline-flex w-full items-center justify-center gap-1.5 rounded-md border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-700 transition-colors hover:bg-rose-50"
                        onclick={() => onunlink?.(metric.id)}
                        data-testid="metric-unlink"
                        title="Drop the reference and keep this as a draft you write yourself"
                    >
                        <Icon icon="lucide:unlink" class="h-3.5 w-3.5" />
                        Unlink and draft it here
                    </button>
                {/if}
            {:else}
                <div>
                    <label class={labelClass} for="metric-field-label-{metric.id}">Label</label>
                    <input
                        id="metric-field-label-{metric.id}"
                        bind:this={labelInput}
                        class={fieldClass}
                        value={metric.label}
                        placeholder="Average price"
                        oninput={(event) => onchange?.({ label: event.currentTarget.value })}
                        data-testid="metric-field-label"
                    />
                </div>

                <div>
                    <label class={labelClass} for="metric-field-description-{metric.id}">
                        Description
                    </label>
                    <textarea
                        id="metric-field-description-{metric.id}"
                        class="{fieldClass} resize-none leading-relaxed"
                        rows="2"
                        value={metric.description ?? ""}
                        placeholder="What this number means in one sentence."
                        oninput={(event) => onchange?.({ description: event.currentTarget.value })}
                        data-testid="metric-field-description"
                    ></textarea>
                </div>

                <div>
                    <label class={labelClass} for="metric-field-expression-{metric.id}">
                        <span>Expression</span>
                        {#if needsExpression}
                            <span class="normal-case tracking-normal text-amber-600">
                                Expression required
                            </span>
                        {/if}
                    </label>
                    <textarea
                        id="metric-field-expression-{metric.id}"
                        class="{fieldClass} resize-none font-mono text-xs leading-relaxed"
                        rows="3"
                        value={metric.expression ?? ""}
                        placeholder="sum(amount)"
                        oninput={(event) => onchange?.({ expression: event.currentTarget.value })}
                        data-testid="metric-field-expression"
                    ></textarea>
                    <p class="mt-1 text-[11px] leading-relaxed text-slate-400">
                        Written as-is. Trellis does not parse SQL.
                    </p>
                </div>

                <div>
                    <label class={labelClass} for="metric-field-dataset-{metric.id}">
                        <span>Dataset</span>
                        <span class="normal-case tracking-normal text-slate-400">optional</span>
                    </label>
                    <div class="relative" bind:this={datasetDropdownRef}>
                        <input
                            id="metric-field-dataset-{metric.id}"
                            class="{fieldClass} pr-8"
                            value={metric.dataset_ref ?? ""}
                            placeholder="fct__order"
                            autocomplete="off"
                            role="combobox"
                            aria-expanded={datasetDropdownOpen && filteredDatasets.length > 0}
                            aria-autocomplete="list"
                            aria-controls="metric-dataset-options-{metric.id}"
                            onfocus={openDatasetDropdown}
                            onblur={() => {
                                datasetDropdownOpen = false;
                                datasetFilterActive = false;
                            }}
                            oninput={(event) => {
                                datasetDropdownOpen = true;
                                datasetFilterActive = true;
                                activeDatasetIndex = 0;
                                onchange?.({ dataset_ref: event.currentTarget.value });
                            }}
                            onkeydown={handleDatasetKeydown}
                            data-testid="metric-field-dataset"
                        />
                        {#if datasets.length > 0}
                            <button
                                type="button"
                                tabindex="-1"
                                class="absolute inset-y-0 right-0 flex items-center pr-2.5 text-slate-400 hover:text-slate-600"
                                aria-label="Toggle dataset options"
                                onmousedown={(event) => event.preventDefault()}
                                onclick={toggleDatasetDropdown}
                                data-testid="metric-dataset-toggle"
                            >
                                <Icon
                                    icon="lucide:chevron-down"
                                    class="h-4 w-4 shrink-0 transition-transform {datasetDropdownOpen
                                        ? 'rotate-180'
                                        : ''}"
                                />
                            </button>
                        {/if}

                        {#if datasetDropdownOpen && filteredDatasets.length > 0}
                            <div
                                class="absolute left-0 z-50 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg ring-1 ring-black/5"
                                onmousedown={(event) => event.preventDefault()}
                            >
                                <ul
                                    id="metric-dataset-options-{metric.id}"
                                    role="listbox"
                                    class="focus:outline-none"
                                    data-testid="metric-dataset-options"
                                >
                                    {#each filteredDatasets as dataset, index (dataset)}
                                        {@const isSelected = dataset === (metric.dataset_ref ?? "")}
                                        {@const isHighlighted = index === activeDatasetIndex}
                                        <!-- svelte-ignore a11y_click_events_have_key_events -->
                                        <li
                                            role="option"
                                            aria-selected={isSelected}
                                            class="relative cursor-pointer select-none py-1.5 pl-3 pr-8 text-sm text-gray-900 transition-colors hover:bg-primary-50 hover:text-primary-700 {isSelected ||
                                            isHighlighted
                                                ? 'bg-primary-50 font-medium text-primary-700'
                                                : ''}"
                                            onclick={() => selectDataset(dataset)}
                                            data-testid="metric-dataset-option"
                                        >
                                            <span class="block truncate font-mono text-xs">{dataset}</span>
                                            {#if isSelected}
                                                <span
                                                    class="absolute inset-y-0 right-0 flex items-center pr-2.5 text-primary-600"
                                                >
                                                    <Icon icon="lucide:check" class="h-4 w-4" />
                                                </span>
                                            {/if}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    </div>
                    <p class="mt-1 text-[11px] leading-relaxed text-slate-400">
                        The semantic-model dataset the metric is written under on push. Free text
                        is allowed; a dataset that is not exported is badged rather than deleted.
                    </p>
                </div>
            {/if}

            {#if warnings.length > 0}
                <div class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
                    <p class="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-amber-800">
                        <Icon icon="lucide:triangle-alert" class="h-3 w-3" />
                        Saved with warnings
                    </p>
                    <ul class="mt-1 space-y-1">
                        {#each warnings as warning (warning)}
                            <li
                                class="text-[11px] leading-relaxed text-amber-800"
                                data-testid="metric-warning"
                            >
                                {warning}
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            {#if error}
                <div
                    class="rounded-md border border-red-200 bg-red-50 px-3 py-2"
                    role="alert"
                    data-testid="metric-save-error"
                >
                    <p class="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-red-800">
                        <Icon icon="lucide:circle-alert" class="h-3 w-3" />
                        Not saved
                    </p>
                    <p class="mt-1 text-[11px] leading-relaxed break-words text-red-800">{error}</p>
                </div>
            {/if}

            {#if incompleteIds.length > 0}
                <p
                    class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] leading-relaxed text-slate-500"
                    data-testid="metric-save-paused"
                >
                    Auto-save paused: {incompleteIds.length} draft
                    {incompleteIds.length === 1 ? "metric needs" : "metrics need"} an expression
                    before the tree can be written.
                </p>
            {/if}
        </div>

        <footer class="flex items-center gap-2 border-t border-slate-200 px-4 py-2 text-[11px] text-slate-500">
            {#if isSaving}
                <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-primary-500"></span>
                Saving&hellip;
            {:else if error}
                <span class="h-1.5 w-1.5 rounded-full bg-red-500"></span>
                Unsaved changes
            {:else if hasUnsavedChanges}
                <span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                Unsaved changes
            {:else}
                <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                All changes saved
            {/if}
        </footer>
    {/if}
</aside>
