<script lang="ts">
    import ConfigCard from './ConfigCard.svelte';
    import ConfigTextInput from './ConfigTextInput.svelte';
    import { getFieldDescription, getFieldValue, type ConfigFormBinding } from '$lib/utils/config-form';

    let {
        config,
        schema,
        onNestedChange,
        modelingStyle,
    }: Pick<ConfigFormBinding, 'config' | 'schema' | 'onNestedChange'> & {
        modelingStyle: string | undefined;
    } = $props();
</script>

{#if modelingStyle === 'dimensional_model'}
    <ConfigCard
        title="Dimensional Modeling"
        tooltip="Configure naming prefixes for dimensional models. trellis uses these patterns to automatically classify models as dimensions or facts."
    >
        <div class="space-y-4">
            <ConfigTextInput
                id="dimension-prefix-input"
                label="Dimension Prefix"
                value={getFieldValue(config, 'dimensional_modeling.inference_patterns.dimension_prefix') || ''}
                oninput={(value) => onNestedChange('dimensional_modeling.inference_patterns.dimension_prefix', value)}
                placeholder="dim_"
                description={getFieldDescription(schema, 'dimensional_modeling.inference_patterns.dimension_prefix')}
            />
            <ConfigTextInput
                id="fact-prefix-input"
                label="Fact Prefix"
                value={getFieldValue(config, 'dimensional_modeling.inference_patterns.fact_prefix') || ''}
                oninput={(value) => onNestedChange('dimensional_modeling.inference_patterns.fact_prefix', value)}
                placeholder="fact_"
                description={getFieldDescription(schema, 'dimensional_modeling.inference_patterns.fact_prefix')}
            />
        </div>
    </ConfigCard>
{/if}

{#if modelingStyle === 'entity_model'}
    <ConfigCard
        title="Entity Modeling"
        tooltip="Set the naming prefix for entity models. trellis uses this pattern to identify and classify entity models in your data model."
    >
        <div class="space-y-4">
            <ConfigTextInput
                id="entity-prefix-input"
                label="Entity Prefix"
                value={getFieldValue(config, 'entity_modeling.inference_patterns.prefix') || ''}
                oninput={(value) => onNestedChange('entity_modeling.inference_patterns.prefix', value)}
                placeholder="entity_"
                description={getFieldDescription(schema, 'entity_modeling.inference_patterns.prefix')}
            />
        </div>
    </ConfigCard>
{/if}
