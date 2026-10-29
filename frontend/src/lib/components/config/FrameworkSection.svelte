<script lang="ts">
    import ConfigCard from './ConfigCard.svelte';
    import ConfigSelectField from './ConfigSelectField.svelte';
    import {
        getEnumOptions,
        getFieldDescription,
        getFieldValue,
        type ConfigFormBinding,
    } from '$lib/utils/config-form';

    let { config, schema, onChange }: Pick<ConfigFormBinding, 'config' | 'schema' | 'onChange'> = $props();
</script>

<ConfigCard
    title="Framework"
    tooltip="Select your transformation framework and modeling approach. This determines how trellis interprets and visualizes your data models."
>
    <div class="space-y-4">
        <ConfigSelectField
            id="framework-select"
            label="Framework"
            value={getFieldValue(config, 'framework')}
            options={getEnumOptions(schema, 'framework', ['dbt-core', 'bruin'])}
            onchange={(value) => onChange('framework', value)}
            description={getFieldDescription(schema, 'framework')}
        />
        <ConfigSelectField
            id="modeling-style-select"
            label="Modeling Style"
            value={getFieldValue(config, 'modeling_style')}
            options={getEnumOptions(schema, 'modeling_style', ['dimensional_model', 'entity_model'])}
            onchange={(value) => onChange('modeling_style', value)}
            description={getFieldDescription(schema, 'modeling_style')}
        />
    </div>
</ConfigCard>
