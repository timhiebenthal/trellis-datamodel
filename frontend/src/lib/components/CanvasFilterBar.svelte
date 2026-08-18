<script lang="ts">
    import Icon from '$lib/components/Icon.svelte';
    import { domainFilter, frameworkModels, nodes, tagFilter } from '$lib/stores';
    import type { EntityData, ModelInfo } from '$lib/types';
    import { normalizeTags } from '$lib/utils';
    import { readModelRef } from '$lib/utils/entity-compat';

    interface Props {
        visibleCount?: number;
        totalCount?: number;
    }

    let { visibleCount, totalCount }: Props = $props();

    function entityData(node: { type?: string; data?: unknown }): EntityData | null {
        return node.type === 'entity' ? (node.data as EntityData) : null;
    }

    function normalizedDomains(data: EntityData): string[] {
        return Array.from(
            new Set([
                ...(Array.isArray(data.domains) ? data.domains : []),
                ...(data.domain ? [data.domain] : []),
            ]),
        )
            .map((domain) => domain.trim())
            .filter(Boolean);
    }

    function modelTags(data: EntityData, modelsById: Map<string, ModelInfo>): string[] {
        const refs = [readModelRef(data), ...(data.additional_models ?? [])].filter(
            (ref): ref is string => Boolean(ref),
        );
        return refs.flatMap((ref) => normalizeTags(modelsById.get(ref)?.tags));
    }

    let entityNodes = $derived($nodes.filter((node) => node.type === 'entity'));
    let modelsById = $derived(new Map($frameworkModels.map((model) => [model.unique_id, model])));

    let allDomains = $derived.by(() =>
        Array.from(
            new Set(
                entityNodes.flatMap((node) => {
                    const data = entityData(node);
                    return data ? normalizedDomains(data) : [];
                }),
            ),
        ).sort((a, b) => a.localeCompare(b)),
    );

    let allTags = $derived.by(() =>
        Array.from(
            new Set(
                entityNodes.flatMap((node) => {
                    const data = entityData(node);
                    if (!data) return [];

                    return [
                        ...normalizeTags(data.tags),
                        ...normalizeTags(data.framework_tags),
                        ...normalizeTags(data.ui_tags),
                        ...modelTags(data, modelsById),
                    ];
                }),
            ),
        ).sort((a, b) => a.localeCompare(b)),
    );

    let isFiltered = $derived($domainFilter.length > 0 || $tagFilter.length > 0);
    let derivedTotalCount = $derived(entityNodes.length);
    let resolvedTotalCount = $derived(totalCount ?? derivedTotalCount);
    let resolvedVisibleCount = $derived(visibleCount ?? resolvedTotalCount);

    function toggleDomain(domain: string) {
        if ($domainFilter.includes(domain)) {
            $domainFilter = $domainFilter.filter((value) => value !== domain);
        } else {
            $domainFilter = [...$domainFilter, domain];
        }
    }

    function toggleTag(tag: string) {
        if ($tagFilter.includes(tag)) {
            $tagFilter = $tagFilter.filter((value) => value !== tag);
        } else {
            $tagFilter = [...$tagFilter, tag];
        }
    }

    function clearFilters() {
        $domainFilter = [];
        $tagFilter = [];
    }
</script>

<div class="pointer-events-none absolute top-4 left-4 z-20 max-w-[min(34rem,calc(100%-2rem))]">
    <div
        class="pointer-events-auto rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-md backdrop-blur-sm"
        role="region"
        aria-label="Canvas filters"
        onpointerdown={(event) => event.stopPropagation()}
    >
        <div class="flex flex-wrap items-center gap-2">
            <div
                class="flex items-center gap-1.5 text-xs font-medium text-slate-700"
                role="status"
                aria-live="polite"
            >
                <Icon icon="lucide:filter" class="h-3.5 w-3.5 text-primary-600" />
                {#if isFiltered}
                    <span>Filtered</span>
                {/if}
                <span>Showing {resolvedVisibleCount} of {resolvedTotalCount} entities</span>
            </div>

            {#if $domainFilter.length > 0}
                <div class="flex flex-wrap gap-1" aria-label="Active Canvas domain filters">
                    {#each $domainFilter as domain}
                        <span
                            data-testid="canvas-filter-domain-chip"
                            class="inline-flex items-center gap-1 rounded border border-primary-200 bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800"
                        >
                            {domain}
                            <button
                                type="button"
                                class="rounded text-primary-700 hover:text-primary-950 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1"
                                aria-label="Remove Canvas domain filter {domain}"
                                onclick={() => toggleDomain(domain)}
                            >
                                <Icon icon="lucide:x" class="h-3 w-3" />
                            </button>
                        </span>
                    {/each}
                </div>
            {/if}

            {#if $tagFilter.length > 0}
                <div class="flex flex-wrap gap-1" aria-label="Active Canvas tag filters">
                    {#each $tagFilter as tag}
                        <span
                            data-testid="canvas-filter-tag-chip"
                            class="inline-flex items-center gap-1 rounded border border-slate-300 bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"
                        >
                            {tag}
                            <button
                                type="button"
                                class="rounded text-slate-600 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-1"
                                aria-label="Remove Canvas tag filter {tag}"
                                onclick={() => toggleTag(tag)}
                            >
                                <Icon icon="lucide:x" class="h-3 w-3" />
                            </button>
                        </span>
                    {/each}
                </div>
            {/if}

            <label class="sr-only" for="canvas-domain-filter">Add Canvas domain filter</label>
            <select
                id="canvas-domain-filter"
                aria-label="Add Canvas domain filter"
                value=""
                onchange={(event) => {
                    const select = event.currentTarget as HTMLSelectElement;
                    if (select.value) toggleDomain(select.value);
                    select.value = '';
                }}
                class="max-w-32 rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 focus:border-primary-600 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
                <option value="" disabled>Add domain...</option>
                {#each allDomains as domain}
                    <option value={domain} disabled={$domainFilter.includes(domain)}>{domain}</option>
                {/each}
            </select>

            <label class="sr-only" for="canvas-tag-filter">Add Canvas tag filter</label>
            <select
                id="canvas-tag-filter"
                aria-label="Add Canvas tag filter"
                value=""
                onchange={(event) => {
                    const select = event.currentTarget as HTMLSelectElement;
                    if (select.value) toggleTag(select.value);
                    select.value = '';
                }}
                class="max-w-32 rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 focus:border-primary-600 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
                <option value="" disabled>Add tag...</option>
                {#each allTags as tag}
                    <option value={tag} disabled={$tagFilter.includes(tag)}>{tag}</option>
                {/each}
            </select>

            {#if isFiltered}
                <button
                    type="button"
                    class="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1"
                    aria-label="Clear Canvas filters"
                    onclick={clearFilters}
                >
                    <Icon icon="lucide:x" class="h-3 w-3" />
                    Clear
                </button>
            {/if}
        </div>
    </div>
</div>
