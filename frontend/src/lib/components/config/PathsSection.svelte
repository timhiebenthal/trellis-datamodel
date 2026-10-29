<script lang="ts">
    import ConfigCard from './ConfigCard.svelte';
    import ConfigTextField from './ConfigTextField.svelte';
    import ConfigPathList from './ConfigPathList.svelte';
    import { getFieldDescription, getFieldValue, type ConfigFormBinding } from '$lib/utils/config-form';

    // Path fields are framework-specific: a dbt project has no pipeline and a
    // Bruin pipeline has no manifest, so showing both sets would invite a user
    // to fill in config nothing reads.
    let {
        config,
        schema,
        onChange,
        selectedFramework,
        validationErrors,
    }: Pick<ConfigFormBinding, 'config' | 'schema' | 'onChange'> & {
        selectedFramework: string;
        validationErrors: Record<string, string>;
    } = $props();

    let dbtModelPaths = $derived(config.dbt_model_paths || []);
    let bruinAssetPaths = $derived(config.bruin_asset_paths || []);
</script>

<ConfigCard
    title="Paths"
    tooltip="Configure file paths to your transformation project and data model files. These paths tell trellis where to find your transformation metadata."
>
    <div class="space-y-4">
        {#if selectedFramework === 'dbt-core'}
            <ConfigTextField
                id="dbt-project-path-input"
                label="dbt Project Path"
                value={getFieldValue(config, 'dbt_project_path')}
                oninput={(value) => onChange('dbt_project_path', value)}
                placeholder="./dbt_project"
                description={getFieldDescription(schema, 'dbt_project_path')}
                error={validationErrors['dbt_project_path']}
            />
            <ConfigTextField
                id="dbt-manifest-path-input"
                label="Manifest Path"
                value={getFieldValue(config, 'dbt_manifest_path')}
                oninput={(value) => onChange('dbt_manifest_path', value)}
                placeholder="target/manifest.json"
                description={getFieldDescription(schema, 'dbt_manifest_path')}
                error={validationErrors['dbt_manifest_path']}
            />
            <ConfigTextField
                id="dbt-catalog-path-input"
                label="Catalog Path"
                value={getFieldValue(config, 'dbt_catalog_path')}
                oninput={(value) => onChange('dbt_catalog_path', value)}
                placeholder="target/catalog.json"
                description={getFieldDescription(schema, 'dbt_catalog_path')}
                error={validationErrors['dbt_catalog_path']}
            />
        {/if}

        {#if selectedFramework === 'bruin'}
            <ConfigTextField
                id="bruin-pipeline-path-input"
                label="Bruin Pipeline Path"
                value={getFieldValue(config, 'bruin_pipeline_path')}
                oninput={(value) => onChange('bruin_pipeline_path', value)}
                placeholder="./pipeline"
                description={getFieldDescription(schema, 'bruin_pipeline_path') || 'Directory holding pipeline.yml and assets/'}
                error={validationErrors['bruin_pipeline_path']}
            />
            <ConfigTextField
                id="bruin-default-asset-type-input"
                label="Default Asset Type"
                value={getFieldValue(config, 'bruin_default_asset_type')}
                oninput={(value) => onChange('bruin_default_asset_type', value)}
                placeholder="duckdb.sql"
            >
                Type used when Trellis creates a new asset for a drafted entity. Platform-specific, e.g. <code>duckdb.sql</code>, <code>bq.sql</code>, <code>sf.sql</code>.
            </ConfigTextField>
            <ConfigPathList
                idPrefix="bruin-asset-paths"
                label="Bruin Asset Paths"
                values={bruinAssetPaths}
                placeholder="02_core"
                emptyText="Empty = all assets included"
                onChange={(values) => onChange('bruin_asset_paths', values)}
            />
        {/if}

        <ConfigTextField
            id="data-model-file-input"
            label="Data Model File"
            value={getFieldValue(config, 'data_model_file')}
            oninput={(value) => onChange('data_model_file', value)}
            placeholder="data_model.yml"
            description={getFieldDescription(schema, 'data_model_file')}
            error={validationErrors['data_model_file']}
        />

        {#if selectedFramework === 'dbt-core'}
            <ConfigTextField
                id="dbt-company-dummy-path-input"
                label="dbt Company Dummy Path"
                value={getFieldValue(config, 'dbt_company_dummy_path') || ''}
                oninput={(value) => onChange('dbt_company_dummy_path', value || null)}
                placeholder="./dbt_company_dummy"
                description={getFieldDescription(schema, 'dbt_company_dummy_path')}
            />
            <ConfigPathList
                idPrefix="dbt-model-paths"
                label="dbt Model Paths"
                values={dbtModelPaths}
                placeholder="3_core"
                emptyText="Empty = all models included"
                onChange={(values) => onChange('dbt_model_paths', values)}
            />
        {/if}
    </div>
</ConfigCard>
