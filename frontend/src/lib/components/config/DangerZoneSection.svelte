<script lang="ts">
    import Icon from '$lib/components/Icon.svelte';
    import Tooltip from '$lib/components/Tooltip.svelte';
    import DangerFeatureCard from './DangerFeatureCard.svelte';
    import DangerToggleRow from './DangerToggleRow.svelte';
    import ConfigSelectField from './ConfigSelectField.svelte';
    import ConfigTextField from './ConfigTextField.svelte';
    import {
        getEnumOptions,
        getFieldDescription,
        getFieldValue,
        isBetaField,
        type ConfigFormBinding,
    } from '$lib/utils/config-form';

    let {
        config,
        schema,
        onNestedChange,
        lineageTooltip,
        acknowledged = $bindable(false),
    }: Pick<ConfigFormBinding, 'config' | 'schema' | 'onNestedChange'> & {
        lineageTooltip: string;
        acknowledged: boolean;
    } = $props();

    let isDangerZoneEnabled = $derived(acknowledged);
    let lineageLayers = $derived(config.lineage?.layers || []);
</script>

<div class="bg-amber-50 border border-amber-200 rounded-lg p-6">
    <div class="flex items-start gap-2 mb-6">
        <Icon icon="lucide:alert-triangle" class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div class="flex-1">
            <div class="flex items-center gap-2">
                <h2 class="text-lg font-semibold text-amber-900">Danger Zone</h2>
                <Tooltip text="Experimental features that may change or be removed. Enable these to access beta functionality like lineage visualization and exposure tracking.">
                    <Icon icon="lucide:help-circle" class="w-4 h-4 text-amber-600 hover:text-amber-700 cursor-help" />
                </Tooltip>
            </div>
            <p class="text-sm text-amber-700 mt-1">
                These features are experimental and may change. Use with caution.
            </p>
        </div>
    </div>

    <div class="mb-6">
        <label class="flex items-start gap-2 cursor-pointer">
            <input
                type="checkbox"
                checked={acknowledged}
                onchange={(e) => acknowledged = e.currentTarget.checked}
                class="mt-1 w-4 h-4 text-primary-600 rounded-full border border-gray-300 focus:ring-0 focus:ring-primary-500 focus:ring-offset-0"
            />
            <span class="text-sm font-medium text-gray-900">
                I understand these features are experimental and may change
            </span>
        </label>
    </div>

    <div class="space-y-6 {isDangerZoneEnabled ? '' : 'opacity-50 pointer-events-none'}">
        <DangerFeatureCard title="Lineage" tooltip={lineageTooltip}>
            <DangerToggleRow
                id="lineage-enabled-toggle"
                label="Lineage Enabled"
                beta={isBetaField(schema, 'lineage.enabled')}
                description={getFieldDescription(schema, 'lineage.enabled')}
                checked={getFieldValue(config, 'lineage.enabled')}
                onchange={(checked) => onNestedChange('lineage.enabled', checked)}
                disabled={!isDangerZoneEnabled}
            />

            <div>
                <label for="lineage-layer-0" class="block text-sm font-medium text-gray-700 mb-1.5">
                    Lineage Layers
                </label>
                {#each lineageLayers as layer, index (index)}
                    <div class="flex gap-2 mb-2">
                        <input
                            id={`lineage-layer-${index}`}
                            type="text"
                            value={layer}
                            oninput={(e) => {
                                const newLayers = [...lineageLayers];
                                newLayers[index] = e.currentTarget.value;
                                onNestedChange('lineage.layers', newLayers);
                            }}
                            placeholder="1_clean"
                            disabled={!isDangerZoneEnabled}
                            class="flex-1 px-3 py-2 text-sm font-mono border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent {isDangerZoneEnabled ? '' : 'opacity-50'}"
                        />
                        <button
                            type="button"
                            onclick={() => {
                                const newLayers = [...lineageLayers];
                                newLayers.splice(index, 1);
                                onNestedChange('lineage.layers', newLayers);
                            }}
                            disabled={!isDangerZoneEnabled}
                            class="px-3 py-2 text-red-600 hover:bg-red-50 border border-red-300 rounded-md text-lg font-medium {isDangerZoneEnabled ? '' : 'opacity-50 cursor-not-allowed'}"
                            title="Remove layer"
                        >
                            ×
                        </button>
                    </div>
                {/each}
                {#if lineageLayers.length === 0}
                    <p class="mt-1.5 text-xs text-gray-500">No layers configured</p>
                {/if}
                <button
                    type="button"
                    onclick={() => onNestedChange('lineage.layers', [...lineageLayers, ''])}
                    disabled={!isDangerZoneEnabled}
                    class="mt-2 px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 border border-primary-300 rounded-md {isDangerZoneEnabled ? '' : 'opacity-50 cursor-not-allowed'}"
                >
                    + Add Layer
                </button>
            </div>
        </DangerFeatureCard>

        <DangerFeatureCard
            title="Exposures"
            tooltip="Track downstream consumption of your data models. Connect dashboards and reports to entities to understand data usage across your organization."
        >
            <DangerToggleRow
                id="exposures-enabled-toggle"
                label="Exposures Enabled"
                beta={isBetaField(schema, 'exposures.enabled')}
                description={getFieldDescription(schema, 'exposures.enabled')}
                checked={getFieldValue(config, 'exposures.enabled')}
                onchange={(checked) => onNestedChange('exposures.enabled', checked)}
                disabled={!isDangerZoneEnabled}
            />
            <ConfigSelectField
                id="exposures-default-layout"
                label="Exposures Default Layout"
                value={getFieldValue(config, 'exposures.default_layout')}
                options={getEnumOptions(schema, 'exposures.default_layout', ['dashboards-as-rows', 'entities-as-rows'])}
                onchange={(value) => onNestedChange('exposures.default_layout', value)}
                description={getFieldDescription(schema, 'exposures.default_layout')}
                disabled={!isDangerZoneEnabled}
            />
        </DangerFeatureCard>

        <DangerFeatureCard
            title="Business Events"
            tooltip="Model business events by annotating natural language sentences with the 7 W's to generate entities and relationships. Works for both dimensional and entity modeling styles."
        >
            <DangerToggleRow
                id="business-events-enabled-toggle"
                label="Business Events Enabled"
                beta={isBetaField(schema, 'business_events.enabled')}
                description={getFieldDescription(schema, 'business_events.enabled') || 'Enable business events modeling to annotate natural language sentences and generate entities'}
                checked={getFieldValue(config, 'business_events.enabled')}
                onchange={(checked) => onNestedChange('business_events.enabled', checked)}
                disabled={!isDangerZoneEnabled}
            />
            <ConfigTextField
                id="business-events-file-input"
                label="Business Events File"
                value={getFieldValue(config, 'business_events.file') || ''}
                oninput={(value) => onNestedChange('business_events.file', value)}
                placeholder="business_events.yml (defaults to same directory as data_model.yml)"
                description={getFieldDescription(schema, 'business_events.file') || 'Path to business events YAML file (optional, defaults to business_events.yml in data model directory)'}
                disabled={!isDangerZoneEnabled}
            />
        </DangerFeatureCard>

        <DangerFeatureCard
            title="Apache Ossie"
            tooltip="Export an Apache Ossie semantic model alongside each push. The model describes the entities bound to your data, using overrides below for the database and schema segments of its dataset names."
        >
            <DangerToggleRow
                id="ossie-enabled-toggle"
                label="Ossie Export Enabled"
                beta={isBetaField(schema, 'ossie.enabled')}
                description={getFieldDescription(schema, 'ossie.enabled') || 'Enable Apache Ossie semantic model export alongside framework pushes'}
                checked={getFieldValue(config, 'ossie.enabled')}
                onchange={(checked) => onNestedChange('ossie.enabled', checked)}
                disabled={!isDangerZoneEnabled}
            />
            <ConfigTextField
                id="ossie-file-input"
                label="Semantic Model File"
                value={getFieldValue(config, 'ossie.file') || ''}
                oninput={(value) => onNestedChange('ossie.file', value)}
                placeholder="semantic_model.yml (defaults to same directory as data_model.yml)"
                description={getFieldDescription(schema, 'ossie.file') || 'Path to the Ossie semantic model file (optional, defaults to semantic_model.yml in data model directory)'}
                disabled={!isDangerZoneEnabled}
            />
            <ConfigTextField
                id="ossie-source-database"
                label="Database Override"
                value={getFieldValue(config, 'ossie.source.database') || ''}
                oninput={(value) => onNestedChange('ossie.source.database', value)}
                description={getFieldDescription(schema, 'ossie.source.database') || 'Leave empty to omit the database segment. Values from the manifest reflect the target that last ran dbt.'}
                disabled={!isDangerZoneEnabled}
            />
            <ConfigTextField
                id="ossie-source-schema"
                label="Schema Override"
                value={getFieldValue(config, 'ossie.source.schema') || ''}
                oninput={(value) => onNestedChange('ossie.source.schema', value)}
                description={getFieldDescription(schema, 'ossie.source.schema') || 'Leave empty to use the schema the adapter reports.'}
                disabled={!isDangerZoneEnabled}
            />
        </DangerFeatureCard>

        <DangerFeatureCard
            title="Metric Tree"
            tooltip="Design a metric tree on its own canvas and emit the drafted metrics into the Apache Ossie document on push."
        >
            <DangerToggleRow
                id="metrics-enabled-toggle"
                label="Metric Tree Enabled"
                beta={isBetaField(schema, 'metrics.enabled')}
                description={getFieldDescription(schema, 'metrics.enabled') || 'Enable the metric tree canvas and metric emission on push'}
                checked={getFieldValue(config, 'metrics.enabled')}
                onchange={(checked) => onNestedChange('metrics.enabled', checked)}
                disabled={!isDangerZoneEnabled}
            />
            <ConfigTextField
                id="metrics-file-input"
                label="Metric Tree File"
                value={getFieldValue(config, 'metrics.file') || ''}
                oninput={(value) => onNestedChange('metrics.file', value)}
                placeholder="metric_tree.yml (defaults to same directory as data_model.yml)"
                description={getFieldDescription(schema, 'metrics.file') || 'Path to the metric tree file (optional, defaults to metric_tree.yml in data model directory)'}
                disabled={!isDangerZoneEnabled}
            />
            <ConfigSelectField
                id="metrics-expression-dialect-select"
                label="Expression Dialect"
                value={getFieldValue(config, 'metrics.expression_dialect') || 'ANSI_SQL'}
                options={getEnumOptions(schema, 'metrics.expression_dialect', ['ANSI_SQL', 'OSSIE_SQL_2026'])}
                onchange={(value) => onNestedChange('metrics.expression_dialect', value)}
                description={getFieldDescription(schema, 'metrics.expression_dialect') || 'Dialect label emitted with each metric expression; it is not validated against the SQL'}
                disabled={!isDangerZoneEnabled}
            />
        </DangerFeatureCard>
    </div>
</div>
