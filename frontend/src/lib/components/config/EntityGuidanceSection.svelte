<script lang="ts">
    import ConfigCard from './ConfigCard.svelte';
    import ConfigTextField from './ConfigTextField.svelte';
    import ConfigToggleSwitch from './ConfigToggleSwitch.svelte';
    import { getFieldDescription, getFieldValue, type ConfigFormBinding } from '$lib/utils/config-form';

    let {
        config,
        schema,
        onNestedChange,
        pushWarningDescription,
    }: Pick<ConfigFormBinding, 'config' | 'schema' | 'onNestedChange'> & {
        pushWarningDescription: string;
    } = $props();
</script>

<ConfigCard
    title="Entity Creation Guidance"
    tooltip="Control the entity creation wizard behavior. Enable validation rules and warnings to ensure data quality when creating new entities."
>
    <div class="space-y-4">
        <div class="flex items-center justify-between">
            <div class="flex-1">
                <label for="entity-guidance-enabled" class="block text-sm font-medium text-gray-700 mb-1.5">
                    Enable Entity Wizard
                </label>
                <p class="text-xs text-gray-500">
                    Turn on entity creation with guided questions for consistent model definitions.
                </p>
            </div>
            <ConfigToggleSwitch
                id="entity-guidance-enabled"
                checked={getFieldValue(config, 'entity_creation_guidance.enabled')}
                onchange={(checked) => onNestedChange('entity_creation_guidance.enabled', checked)}
            />
        </div>

        <div class="flex items-center justify-between">
            <div class="flex-1">
                <label for="entity-guidance-push-warning" class="block text-sm font-medium text-gray-700 mb-1.5">
                    Push Warning Enabled
                </label>
                <p class="text-xs text-gray-500">
                    {pushWarningDescription}
                </p>
            </div>
            <ConfigToggleSwitch
                id="entity-guidance-push-warning"
                checked={getFieldValue(config, 'entity_creation_guidance.push_warning_enabled')}
                onchange={(checked) => onNestedChange('entity_creation_guidance.push_warning_enabled', checked)}
            />
        </div>

        <ConfigTextField
            id="entity-guidance-min-description"
            label="Min Description Length"
            type="number"
            min="0"
            mono={false}
            value={getFieldValue(config, 'entity_creation_guidance.min_description_length')}
            oninput={(value) => onNestedChange('entity_creation_guidance.min_description_length', parseInt(value) || 0)}
            description={getFieldDescription(schema, 'entity_creation_guidance.min_description_length')}
        />

        <div>
            <label for="entity-guidance-disabled-0" class="block text-sm font-medium text-gray-700 mb-1.5">
                Disabled Guidance
            </label>
            {#each getFieldValue(config, 'entity_creation_guidance.disabled_guidance') || [] as item, index}
                <input
                    id={`entity-guidance-disabled-${index}`}
                    type="text"
                    value={item}
                    oninput={(e) => {
                        const newItems = [...(getFieldValue(config, 'entity_creation_guidance.disabled_guidance') || [])];
                        newItems[index] = e.currentTarget.value;
                        onNestedChange('entity_creation_guidance.disabled_guidance', newItems);
                    }}
                    placeholder="attribute_suggestions"
                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
            {/each}
            {#if (getFieldValue(config, 'entity_creation_guidance.disabled_guidance') || []).length === 0}
                <p class="mt-1.5 text-xs text-gray-500">Empty = all guidance enabled</p>
            {/if}
        </div>
    </div>
</ConfigCard>
