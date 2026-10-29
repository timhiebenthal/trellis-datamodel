<script lang="ts">
    import ConfigCard from './ConfigCard.svelte';
    import CanvasFilterList from './CanvasFilterList.svelte';
    import { frameworkModels, nodes } from '$lib/stores';
    import { normalizeTags } from '$lib/utils/entity-tags';
    import { readModelRef } from '$lib/utils/entity-compat';
    import { getFieldValue, type ConfigFormBinding } from '$lib/utils/config-form';

    let { config, onChange, onNestedChange }: Pick<ConfigFormBinding, 'config' | 'onChange' | 'onNestedChange'> = $props();

    let canvasDefaultFilters = $derived(config.canvas?.default_filters || {});
    let canvasDefaultDomains = $derived(Array.isArray(canvasDefaultFilters.domains) ? canvasDefaultFilters.domains : []);
    let canvasDefaultTags = $derived(Array.isArray(canvasDefaultFilters.tags) ? canvasDefaultFilters.tags : []);
    let canvasEntityData = $derived($nodes
        .filter((node) => node.type === 'entity')
        .map((node) => node.data as Record<string, unknown>));
    let availableCanvasDomains = $derived(Array.from(
        new Set(
            canvasEntityData.flatMap((entity) => [
                ...normalizeTags(entity.domain),
                ...normalizeTags(entity.domains),
            ]),
        ),
    ).sort());
    let availableCanvasTags = $derived(Array.from(
        new Set(
            canvasEntityData.flatMap((entity) => {
                const modelRefs = [
                    readModelRef(entity),
                    ...(Array.isArray(entity.additional_models) ? entity.additional_models : []),
                ].filter((ref): ref is string => typeof ref === 'string' && ref.length > 0);
                const modelTags = $frameworkModels
                    .filter((model) => modelRefs.includes(model.unique_id))
                    .flatMap((model) => normalizeTags(model.tags));
                return [
                    ...normalizeTags(entity.tags),
                    ...normalizeTags(entity.framework_tags),
                    ...normalizeTags(entity.ui_tags),
                    ...modelTags,
                ];
            }),
        ),
    ).sort());
</script>

<ConfigCard
    title="Canvas"
    tooltip="Choose the default landing page and filters for this shared project."
    headerClass="mb-2"
>
    <p class="mb-5 text-sm text-gray-600">
        These are shared project defaults stored in <code class="font-mono text-xs">trellis.yml</code>, not personal preferences.
        Changes are written to the shared project configuration when you select Apply Configuration.
    </p>
    <div class="space-y-5">
        <div>
            <label for="canvas-start-page-select" class="block text-sm font-medium text-gray-700 mb-1.5">
                Start Page
            </label>
            <select
                id="canvas-start-page-select"
                value={getFieldValue(config, 'start_page') || 'canvas'}
                onchange={(e) => onChange('start_page', e.currentTarget.value)}
                class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
            >
                <option value="canvas">Canvas</option>
                <option value="entity-list">Entity List</option>
            </select>
            <p class="mt-1.5 text-xs text-gray-500">
                Select which page opens when navigating to the project root.
            </p>
        </div>

        <CanvasFilterList
            label="Default Domains"
            name="Domain"
            plural="domains"
            idPrefix="canvas-default-domain"
            values={canvasDefaultDomains}
            available={availableCanvasDomains}
            onChange={(values) => onNestedChange('canvas.default_filters.domains', values)}
        />

        <CanvasFilterList
            label="Default Tags"
            name="Tag"
            plural="tags"
            idPrefix="canvas-default-tag"
            values={canvasDefaultTags}
            available={availableCanvasTags}
            onChange={(values) => onNestedChange('canvas.default_filters.tags', values)}
        />
    </div>
</ConfigCard>
