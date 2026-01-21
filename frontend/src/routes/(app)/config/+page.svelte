<script lang="ts">
    import { onMount } from 'svelte';
    import { getConfig, getConfigSchema, updateConfig, validateConfig, reloadConfig } from '$lib/api';
    import type { ConfigGetResponse, ConfigFieldMetadata, ConfigSchema } from '$lib/api';
    import Icon from '$lib/components/Icon.svelte';
    import Tooltip from '$lib/components/Tooltip.svelte';

    let loading = true;
    let saving = false;
    let error: string | null = null;

    // Config state
    let config: Record<string, any> = {};
    let schema: ConfigSchema = { fields: {}, beta_flags: [] };
    let fileInfo: { path: string; mtime: number; hash: string } | null = null;

    // Form validation state
    let validationErrors: Record<string, string> = {};
    let showValidationSummary = false;

    // Danger Zone acknowledgment
    let dangerZoneAcknowledged = false;

    // Reactive state for danger zone
    $: isDangerZoneEnabled = dangerZoneAcknowledged;

    // Conflict state
    let conflictWarning: string | null = null;
    let conflictInfo: any = null;

    // Reactive modeling style for conditional rendering
    $: modelingStyle = config.modeling_style;

    // Entity guidance toggle state for dependent fields
    $: entityGuidanceEnabled = !!config?.entity_creation_guidance?.enabled;
    $: if (!entityGuidanceEnabled && getFieldValue('entity_creation_guidance.push_warning_enabled')) {
        handleNestedFieldChange('entity_creation_guidance.push_warning_enabled', false);
    }
    
    // Reactive lineage layers for UI updates
    $: lineageLayers = config.lineage?.layers || [];

    onMount(async () => {
        await loadConfig();
        loading = false;
    });

    async function loadConfig() {
        try {
            const response: ConfigGetResponse = await getConfig();

            if (response.error) {
                error = response.error;
                return;
            }

            config = response.config || {};
            schema = response.schema_metadata;
            fileInfo = response.file_info || null;

            // Ensure defaults when schema metadata is missing
            if (!schema?.fields || Object.keys(schema.fields).length === 0) {
                schema = {
                    fields: {
                        framework: {
                            type: 'enum',
                            enum_values: ['dbt-core'],
                            default: 'dbt-core',
                            required: true,
                            description: 'Transformation framework',
                            beta: false,
                        },
                        modeling_style: {
                            type: 'enum',
                            enum_values: ['dimensional_model', 'entity_model'],
                            default: 'entity_model',
                            required: true,
                            description: 'Modeling style approach',
                            beta: false,
                        },
                        'exposures.default_layout': {
                            type: 'enum',
                            enum_values: ['dashboards-as-rows', 'entities-as-rows'],
                            default: 'dashboards-as-rows',
                            required: false,
                            description: 'Default layout for exposures visualization',
                            beta: true,
                        },
                    },
                    beta_flags: ['lineage.enabled', 'lineage.layers', 'exposures.enabled', 'exposures.default_layout'],
                };
            }

            if (!config.framework) {
                config.framework = 'dbt-core';
            }
            if (!config.modeling_style) {
                config.modeling_style = 'entity_model';
            }
            if (!getFieldValue('exposures.default_layout')) {
                handleNestedFieldChange('exposures.default_layout', 'dashboards-as-rows');
            }

            // Trigger reactivity by reassigning config
            config = { ...config };

            // Determine if beta features are enabled
            dangerZoneAcknowledged = false;
        } catch (e) {
            console.error("Failed to load config:", e);
            error = e instanceof Error ? e.message : "Failed to load configuration";
        }
    }

    async function handleApply(event?: Event) {
        if (event) {
            event.preventDefault();
        }
        saving = true;
        error = null;
        validationErrors = {};
        conflictWarning = null;

        try {
            // Validate config first
            const validation = await validateConfig(config);
            if (!validation.valid) {
                // Parse validation errors into field-level errors
                if (validation.error) {
                    const errorParts = validation.error.split('; ');
                    errorParts.forEach(part => {
                        const [field, message] = part.split(': ');
                        if (field && message) {
                            validationErrors[field] = message;
                        }
                    });
                }
                showValidationSummary = true;
                saving = false;
                return;
            }

            // Apply config with conflict detection
            const response = await updateConfig(
                config,
                fileInfo?.mtime,
                fileInfo?.hash
            );

            // Update file info with new values
            fileInfo = response.file_info;

            // Reload backend config to apply changes
            try {
                await reloadConfig();
                // Show success message and reload page to pick up new config values
                showSuccessToast();
                // Reload page after a short delay to allow toast to be visible
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } catch (reloadError) {
                // Reload failed - show error but keep old runtime state
                const reloadMessage = reloadError instanceof Error ? reloadError.message : String(reloadError);
                showErrorToast(`Configuration saved but reload failed: ${reloadMessage}`);
            }

            // Reset saving state after successful save
            saving = false;
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e);

            if (message.startsWith('CONFLICT:')) {
                try {
                    const conflictData = JSON.parse(message.replace('CONFLICT: ', ''));
                    conflictWarning = conflictData.message || 'Config file has been modified by another process';
                    conflictInfo = conflictData.conflict;
                    saving = false;
                } catch {
                    conflictWarning = 'Config file has been modified by another process';
                    saving = false;
                }
            } else {
                error = message;
                saving = false;
            }
        }
    }

    function showSuccessToast() {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-fade-in';
        toast.textContent = '✓ Configuration saved and reloaded successfully';
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    function showErrorToast(message: string) {
        // Error toast notification
        const toast = document.createElement('div');
        toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-fade-in';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    function handleReload() {
        loadConfig();
        conflictWarning = null;
        conflictInfo = null;
    }

    function handleForceOverwrite() {
        // Clear file info to force overwrite
        fileInfo = null;
        conflictWarning = null;
        conflictInfo = null;
        handleApply();
    }

    function handleFieldChange(field: string, value: any) {
        config = { ...config, [field]: value };
        delete validationErrors[field];
    }

    function handleNestedFieldChange(path: string, value: any) {
        const parts = path.split('.');
        const newConfig = { ...config };

        let current: any = newConfig;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!current[parts[i]]) {
                current[parts[i]] = {};
            } else {
                // Deep clone the nested object to ensure Svelte detects the change
                current[parts[i]] = Array.isArray(current[parts[i]]) 
                    ? [...current[parts[i]]]
                    : { ...current[parts[i]] };
            }
            current = current[parts[i]];
        }

        current[parts[parts.length - 1]] = value;

        config = newConfig;
        delete validationErrors[path];
    }

    function getFieldValue(path: string): any {
        const parts = path.split('.');
        let current: any = config;

        for (const part of parts) {
            if (current && current[part] !== undefined) {
                current = current[part];
            } else {
                return null;
            }
        }

        return current;
    }

    function getFieldMetadata(path: string): ConfigFieldMetadata | null {
        return schema.fields[path] || null;
    }

    function isBetaField(path: string): boolean {
        return schema.beta_flags.includes(path);
    }

    function getEnumOptions(path: string, fallback: string[]): string[] {
        const options = getFieldMetadata(path)?.enum_values;
        if (options && options.length > 0) return options;
        return fallback;
    }
</script>

<svelte:head>
    <title>trellis - Configuration</title>
    <meta name="description" content="Configure trellis data model settings" />
</svelte:head>

    <div class="flex-1 overflow-y-auto">
        <div class="max-w-4xl mx-auto px-4 py-8">
            {#if loading}
                <div class="flex items-center justify-center py-12">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
                </div>
            {:else}
                <div class="mb-6">
                    <h1 class="text-3xl font-bold text-gray-900 mb-2">Configuration</h1>
                    <p class="text-gray-600">
                        Configure your trellis data model settings. Changes are validated and backed up before applying.
                    </p>
                </div>

                {#if error}
                    <div class="mb-6 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
                        <div class="flex items-start gap-2">
                            <Icon icon="lucide:alert-circle" class="w-5 h-5 mt-0.5 flex-shrink-0" />
                            <div>
                                <p class="font-medium">Failed to load configuration</p>
                                <p class="text-sm mt-1">{error}</p>
                                <button
                                    onclick={handleReload}
                                    class="mt-3 px-3 py-1.5 text-sm font-medium bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                                >
                                    Reload
                                </button>
                            </div>
                        </div>
                    </div>

                {:else if conflictWarning}
                    <div class="mb-6 bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg">
                        <div class="flex items-start gap-2">
                            <Icon icon="lucide:alert-triangle" class="w-5 h-5 mt-0.5 flex-shrink-0" />
                            <div class="flex-1">
                                <p class="font-medium">Configuration Conflict</p>
                                <p class="text-sm mt-1">{conflictWarning}</p>
                                <div class="flex gap-2 mt-3">
                                    <button
                                        onclick={handleReload}
                                        class="px-3 py-1.5 text-sm font-medium bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors"
                                    >
                                        Reload Changes
                                    </button>
                                    <button
                                        onclick={handleForceOverwrite}
                                        class="px-3 py-1.5 text-sm font-medium bg-white text-amber-700 border border-amber-300 rounded hover:bg-amber-50 transition-colors"
                                    >
                                        Force Overwrite
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                {/if}

                {#if showValidationSummary}
                    <div class="mb-6 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
                        <div class="flex items-start gap-2">
                            <Icon icon="lucide:alert-circle" class="w-5 h-5 mt-0.5 flex-shrink-0" />
                            <div>
                                <p class="font-medium">Validation Errors</p>
                                <p class="text-sm mt-1">Please fix the following errors before applying:</p>
                                <ul class="mt-2 space-y-1 text-sm">
                                    {#each Object.entries(validationErrors) as [key, message]}
                                        <li class="flex gap-2">
                                            <span class="font-mono text-red-700 bg-red-100 px-1.5 py-0.5 rounded">{key}</span>
                                            <span>{message}</span>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        </div>
                    </div>
                {/if}

                <form onsubmit={handleApply} class="space-y-8">
                    <!-- Action Buttons -->
                    <div class="flex items-center justify-end gap-3 mb-6">
                        <button
                            type="button"
                            onclick={handleReload}
                            disabled={saving}
                            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                        >
                            Reset Changes
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            class="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {#if saving}
                                <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8 0 0 4 0 0 0 0 4 0 0 0 0 4 0 4 0 0 4 0 0 4 0 0 0 4 0 0 4 0 0 0 0 4 0 0 0 0z"></path>
                                </svg>
                            {/if}
                            Apply Configuration
                        </button>
                    </div>
                    <!-- Framework Section -->
                    <div class="bg-white border border-gray-200 rounded-lg p-6">
                        <div class="flex items-center gap-2 mb-4">
                            <h2 class="text-lg font-semibold text-gray-900">Framework</h2>
                            <Tooltip text="Select your transformation framework and modeling approach. This determines how trellis interprets and visualizes your data models.">
                                <Icon icon="lucide:help-circle" class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                            </Tooltip>
                        </div>
                        <div class="space-y-4">
                            <div>
                                <label for="framework-select" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Framework
                                </label>
                                <select
                                    id="framework-select"
                                    value={getFieldValue('framework')}
                                    onchange={(e) => handleFieldChange('framework', e.currentTarget.value)}
                                    class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                >
                                    {#each getEnumOptions('framework', ['dbt-core']) as value}
                                        <option value={value}>{value}</option>
                                    {/each}
                                </select>
                                {#if getFieldMetadata('framework')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('framework')?.description}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="modeling-style-select" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Modeling Style
                                </label>
                                <select
                                    id="modeling-style-select"
                                    value={getFieldValue('modeling_style')}
                                    onchange={(e) => handleFieldChange('modeling_style', e.currentTarget.value)}
                                    class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                >
                                    {#each getEnumOptions('modeling_style', ['dimensional_model', 'entity_model']) as value}
                                        <option value={value}>{value}</option>
                                    {/each}
                                </select>
                                {#if getFieldMetadata('modeling_style')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('modeling_style')?.description}</p>
                                {/if}
                            </div>
                        </div>
                    </div>

                    <!-- Paths Section -->
                    <div class="bg-white border border-gray-200 rounded-lg p-6">
                        <div class="flex items-center gap-2 mb-4">
                            <h2 class="text-lg font-semibold text-gray-900">Paths</h2>
                            <Tooltip text="Configure file paths to your dbt project artifacts and data model files. These paths tell trellis where to find your transformation metadata.">
                                <Icon icon="lucide:help-circle" class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                            </Tooltip>
                        </div>
                        <div class="space-y-4">
                            <div>
                                <label for="dbt-project-path-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    dbt Project Path
                                </label>
                                <input
                                    id="dbt-project-path-input"
                                    type="text"
                                    value={getFieldValue('dbt_project_path')}
                                    oninput={(e) => handleFieldChange('dbt_project_path', e.currentTarget.value)}
                                    placeholder="./dbt_project"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {validationErrors['dbt_project_path'] ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}"
                                />
                                {#if getFieldMetadata('dbt_project_path')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('dbt_project_path')?.description}</p>
                                {/if}
                                {#if validationErrors['dbt_project_path']}
                                    <p class="mt-1 text-xs text-red-600">{validationErrors['dbt_project_path']}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="dbt-manifest-path-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Manifest Path
                                </label>
                                <input
                                    id="dbt-manifest-path-input"
                                    type="text"
                                    value={getFieldValue('dbt_manifest_path')}
                                    oninput={(e) => handleFieldChange('dbt_manifest_path', e.currentTarget.value)}
                                    placeholder="target/manifest.json"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {validationErrors['dbt_manifest_path'] ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}"
                                />
                                {#if getFieldMetadata('dbt_manifest_path')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('dbt_manifest_path')?.description}</p>
                                {/if}
                                {#if validationErrors['dbt_manifest_path']}
                                    <p class="mt-1 text-xs text-red-600">{validationErrors['dbt_manifest_path']}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="dbt-catalog-path-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Catalog Path
                                </label>
                                <input
                                    id="dbt-catalog-path-input"
                                    type="text"
                                    value={getFieldValue('dbt_catalog_path')}
                                    oninput={(e) => handleFieldChange('dbt_catalog_path', e.currentTarget.value)}
                                    placeholder="target/catalog.json"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {validationErrors['dbt_catalog_path'] ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}"
                                />
                                {#if getFieldMetadata('dbt_catalog_path')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('dbt_catalog_path')?.description}</p>
                                {/if}
                                {#if validationErrors['dbt_catalog_path']}
                                    <p class="mt-1 text-xs text-red-600">{validationErrors['dbt_catalog_path']}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="data-model-file-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Data Model File
                                </label>
                                <input
                                    id="data-model-file-input"
                                    type="text"
                                    value={getFieldValue('data_model_file')}
                                    oninput={(e) => handleFieldChange('data_model_file', e.currentTarget.value)}
                                    placeholder="data_model.yml"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {validationErrors['data_model_file'] ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}"
                                />
                                {#if getFieldMetadata('data_model_file')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('data_model_file')?.description}</p>
                                {/if}
                                {#if validationErrors['data_model_file']}
                                    <p class="mt-1 text-xs text-red-600">{validationErrors['data_model_file']}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="dbt-company-dummy-path-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    dbt Company Dummy Path
                                </label>
                                <input
                                    id="dbt-company-dummy-path-input"
                                    type="text"
                                    value={getFieldValue('dbt_company_dummy_path') || ''}
                                    oninput={(e) => handleFieldChange('dbt_company_dummy_path', e.currentTarget.value || null)}
                                    placeholder="./dbt_company_dummy"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                />
                                {#if getFieldMetadata('dbt_company_dummy_path')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('dbt_company_dummy_path')?.description}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="dbt-model-paths-0" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    dbt Model Paths
                                </label>
                                {#each getFieldValue('dbt_model_paths') || [] as path, index}
                                    <input
                                        id={`dbt-model-paths-${index}`}
                                        type="text"
                                        value={path}
                                        oninput={(e) => {
                                            const newPaths = [...(getFieldValue('dbt_model_paths') || [])];
                                            newPaths[index] = e.currentTarget.value;
                                            handleFieldChange('dbt_model_paths', newPaths);
                                        }}
                                        placeholder="3_core"
                                        class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                    />
                                {/each}
                                {#if (getFieldValue('dbt_model_paths') || []).length === 0}
                                    <p class="mt-1.5 text-xs text-gray-500">Empty = all models included</p>
                                {/if}
                            </div>
                        </div>
                    </div>

                    <!-- Entity Creation Guidance Section -->
                    <div class="bg-white border border-gray-200 rounded-lg p-6">
                        <div class="flex items-center gap-2 mb-4">
                            <h2 class="text-lg font-semibold text-gray-900">Entity Creation Guidance</h2>
                            <Tooltip text="Control the entity creation wizard behavior. Enable validation rules and warnings to ensure data quality when creating new entities.">
                                <Icon icon="lucide:help-circle" class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                            </Tooltip>
                        </div>
                        <div class="space-y-4">
                            <div class="flex items-center justify-between">
                                <div class="flex-1">
                                    <label for="entity-guidance-enabled" class="block text-sm font-medium text-gray-700 mb-1.5">
                                        Enable Entity Wizard
                                    </label>
                                    {#if getFieldMetadata('entity_creation_guidance.enabled')?.description}
                                        <p class="text-xs text-gray-500">{getFieldMetadata('entity_creation_guidance.enabled')?.description}</p>
                                    {/if}
                                </div>
                                <label class="relative inline-flex items-center cursor-pointer">
                                    <input
                                        id="entity-guidance-enabled"
                                        type="checkbox"
                                        checked={getFieldValue('entity_creation_guidance.enabled')}
                                        onchange={(e) => handleNestedFieldChange('entity_creation_guidance.enabled', e.currentTarget.checked)}
                                        class="sr-only peer focus:ring-0 focus:ring-offset-0"
                                    />
                                    <div class="w-11 h-6 bg-gray-200 rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 peer-checked:bg-primary-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                                </label>
                            </div>

                            <div class="flex items-center justify-between">
                                <div class="flex-1">
                                    <label for="entity-guidance-push-warning" class="block text-sm font-medium text-gray-700 mb-1.5">
                                        Push Warning Enabled
                                    </label>
                                    {#if getFieldMetadata('entity_creation_guidance.push_warning_enabled')?.description}
                                        <p class="text-xs text-gray-500">{getFieldMetadata('entity_creation_guidance.push_warning_enabled')?.description}</p>
                                    {/if}
                                </div>
                                <label class="relative inline-flex items-center cursor-pointer">
                                    <input
                                        id="entity-guidance-push-warning"
                                        type="checkbox"
                                        checked={getFieldValue('entity_creation_guidance.push_warning_enabled')}
                                        onchange={(e) => handleNestedFieldChange('entity_creation_guidance.push_warning_enabled', e.currentTarget.checked)}
                                        class="sr-only peer focus:ring-0 focus:ring-offset-0"
                                    />
                                    <div class="w-11 h-6 bg-gray-200 rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 peer-checked:bg-primary-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                                </label>
                            </div>

                            <div>
                                <label for="entity-guidance-min-description" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Min Description Length
                                </label>
                                <input
                                    id="entity-guidance-min-description"
                                    type="number"
                                    min="0"
                                    value={getFieldValue('entity_creation_guidance.min_description_length')}
                                    oninput={(e) => handleNestedFieldChange('entity_creation_guidance.min_description_length', parseInt(e.currentTarget.value) || 0)}
                                    class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                />
                                {#if getFieldMetadata('entity_creation_guidance.min_description_length')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('entity_creation_guidance.min_description_length')?.description}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="entity-guidance-disabled-0" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Disabled Guidance
                                </label>
                                {#each getFieldValue('entity_creation_guidance.disabled_guidance') || [] as item, index}
                                    <input
                                        id={`entity-guidance-disabled-${index}`}
                                        type="text"
                                        value={item}
                                        oninput={(e) => {
                                            const newItems = [...(getFieldValue('entity_creation_guidance.disabled_guidance') || [])];
                                            newItems[index] = e.currentTarget.value;
                                            handleNestedFieldChange('entity_creation_guidance.disabled_guidance', newItems);
                                        }}
                                        placeholder="attribute_suggestions"
                                        class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    />
                                {/each}
                                {#if (getFieldValue('entity_creation_guidance.disabled_guidance') || []).length === 0}
                                    <p class="mt-1.5 text-xs text-gray-500">Empty = all guidance enabled</p>
                                {/if}
                            </div>
                        </div>
                    </div>

                    <!-- Dimensional Modeling Section -->
                    {#if modelingStyle === 'dimensional_model'}
                    <div class="bg-white border border-gray-200 rounded-lg p-6">
                        <div class="flex items-center gap-2 mb-4">
                            <h2 class="text-lg font-semibold text-gray-900">Dimensional Modeling</h2>
                            <Tooltip text="Configure naming prefixes for dimensional models. trellis uses these patterns to automatically classify models as dimensions or facts.">
                                <Icon icon="lucide:help-circle" class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                            </Tooltip>
                        </div>
                        <div class="space-y-4">
                            <div>
                                <label for="dimension-prefix-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Dimension Prefix
                                </label>
                                <input
                                    id="dimension-prefix-input"
                                    type="text"
                                    value={getFieldValue('dimensional_modeling.inference_patterns.dimension_prefix') || ''}
                                    oninput={(e) => handleNestedFieldChange('dimensional_modeling.inference_patterns.dimension_prefix', e.currentTarget.value)}
                                    placeholder="dim_"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                />
                                {#if getFieldMetadata('dimensional_modeling.inference_patterns.dimension_prefix')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('dimensional_modeling.inference_patterns.dimension_prefix')?.description}</p>
                                {/if}
                            </div>

                            <div>
                                <label for="fact-prefix-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Fact Prefix
                                </label>
                                <input
                                    id="fact-prefix-input"
                                    type="text"
                                    value={getFieldValue('dimensional_modeling.inference_patterns.fact_prefix') || ''}
                                    oninput={(e) => handleNestedFieldChange('dimensional_modeling.inference_patterns.fact_prefix', e.currentTarget.value)}
                                    placeholder="fact_"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                />
                                {#if getFieldMetadata('dimensional_modeling.inference_patterns.fact_prefix')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('dimensional_modeling.inference_patterns.fact_prefix')?.description}</p>
                                {/if}
                            </div>
                        </div>
                    </div>
                    {/if}

                    <!-- Entity Modeling Section -->
                    {#if modelingStyle === 'entity_model'}
                    <div class="bg-white border border-gray-200 rounded-lg p-6">
                        <div class="flex items-center gap-2 mb-4">
                            <h2 class="text-lg font-semibold text-gray-900">Entity Modeling</h2>
                            <Tooltip text="Set the naming prefix for entity models. trellis uses this pattern to identify and classify entity models in your data model.">
                                <Icon icon="lucide:help-circle" class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                            </Tooltip>
                        </div>
                        <div class="space-y-4">
                            <div>
                                <label for="entity-prefix-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                    Entity Prefix
                                </label>
                                <input
                                    id="entity-prefix-input"
                                    type="text"
                                    value={getFieldValue('entity_modeling.inference_patterns.prefix') || ''}
                                    oninput={(e) => handleNestedFieldChange('entity_modeling.inference_patterns.prefix', e.currentTarget.value)}
                                    placeholder="entity_"
                                    class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
                                />
                                {#if getFieldMetadata('entity_modeling.inference_patterns.prefix')?.description}
                                    <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('entity_modeling.inference_patterns.prefix')?.description}</p>
                                {/if}
                            </div>
                        </div>
                    </div>
                {/if}

                    <!-- Danger Zone Section -->
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
                                    checked={dangerZoneAcknowledged}
                                    onchange={(e) => dangerZoneAcknowledged = e.currentTarget.checked}
                                    class="mt-1 w-4 h-4 text-primary-600 rounded-full border border-gray-300 focus:ring-0 focus:ring-primary-500 focus:ring-offset-0"
                                />
                                <span class="text-sm font-medium text-gray-900">
                                    I understand these features are experimental and may change
                                </span>
                            </label>
                        </div>

                        <div class="space-y-6 {isDangerZoneEnabled ? '' : 'opacity-50 pointer-events-none'}">
                            <!-- Lineage Container -->
                            <div class="bg-white border border-amber-200 rounded-lg p-4">
                                <div class="flex items-center gap-2 mb-4">
                                    <h3 class="text-base font-semibold text-amber-900">Lineage</h3>
                                    <Tooltip text="Visualize data lineage across your dbt models. Configure layers to organize models by transformation stages (e.g., staging, intermediate, marts).">
                                        <Icon icon="lucide:help-circle" class="w-4 h-4 text-amber-600 hover:text-amber-700 cursor-help" />
                                    </Tooltip>
                                </div>
                                <div class="space-y-4">
                                    <div class="flex items-center justify-between">
                                        <div class="flex-1">
                                            <div class="flex items-center gap-2">
                                                <label for="lineage-enabled-toggle" class="block text-sm font-medium text-gray-700">
                                                    Lineage Enabled
                                                </label>
                                                {#if isBetaField('lineage.enabled')}
                                                    <span class="px-2 py-0.5 text-xs font-medium bg-amber-200 text-amber-800 rounded">Beta</span>
                                                {/if}
                                            </div>
                                            {#if getFieldMetadata('lineage.enabled')?.description}
                                                <p class="text-xs text-gray-500 mt-1">{getFieldMetadata('lineage.enabled')?.description}</p>
                                            {/if}
                                        </div>
                                        <label class="relative inline-flex items-center cursor-pointer">
                                            <input
                                                id="lineage-enabled-toggle"
                                                type="checkbox"
                                                checked={getFieldValue('lineage.enabled')}
                                                onchange={(e) => handleNestedFieldChange('lineage.enabled', e.currentTarget.checked)}
                                                disabled={!isDangerZoneEnabled}
                                                class="sr-only peer focus:ring-0 focus:ring-offset-0"
                                            />
                                            <div class="w-11 h-6 bg-gray-200 rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 peer-checked:bg-primary-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full {isDangerZoneEnabled ? '' : 'opacity-50'}"></div>
                                        </label>
                                    </div>

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
                                                        handleNestedFieldChange('lineage.layers', newLayers);
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
                                                        handleNestedFieldChange('lineage.layers', newLayers);
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
                                            onclick={() => {
                                                const newLayers = [...lineageLayers];
                                                newLayers.push('');
                                                handleNestedFieldChange('lineage.layers', newLayers);
                                            }}
                                            disabled={!isDangerZoneEnabled}
                                            class="mt-2 px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 border border-primary-300 rounded-md {isDangerZoneEnabled ? '' : 'opacity-50 cursor-not-allowed'}"
                                        >
                                            + Add Layer
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Exposures Container -->
                            <div class="bg-white border border-amber-200 rounded-lg p-4">
                                <div class="flex items-center gap-2 mb-4">
                                    <h3 class="text-base font-semibold text-amber-900">Exposures</h3>
                                    <Tooltip text="Track downstream consumption of your data models. Connect dashboards and reports to entities to understand data usage across your organization.">
                                        <Icon icon="lucide:help-circle" class="w-4 h-4 text-amber-600 hover:text-amber-700 cursor-help" />
                                    </Tooltip>
                                </div>
                                <div class="space-y-4">
                                    <div class="flex items-center justify-between">
                                        <div class="flex-1">
                                            <div class="flex items-center gap-2">
                                                <label for="exposures-enabled-toggle" class="block text-sm font-medium text-gray-700">
                                                    Exposures Enabled
                                                </label>
                                                {#if isBetaField('exposures.enabled')}
                                                    <span class="px-2 py-0.5 text-xs font-medium bg-amber-200 text-amber-800 rounded">Beta</span>
                                                {/if}
                                            </div>
                                            {#if getFieldMetadata('exposures.enabled')?.description}
                                                <p class="text-xs text-gray-500 mt-1">{getFieldMetadata('exposures.enabled')?.description}</p>
                                            {/if}
                                        </div>
                                        <label class="relative inline-flex items-center cursor-pointer">
                                            <input
                                                id="exposures-enabled-toggle"
                                                type="checkbox"
                                                checked={getFieldValue('exposures.enabled')}
                                                onchange={(e) => handleNestedFieldChange('exposures.enabled', e.currentTarget.checked)}
                                                disabled={!isDangerZoneEnabled}
                                                class="sr-only peer focus:ring-0 focus:ring-offset-0"
                                            />
                                            <div class="w-11 h-6 bg-gray-200 rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 peer-checked:bg-primary-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full {isDangerZoneEnabled ? '' : 'opacity-50'}"></div>
                                        </label>
                                    </div>

                                    <div>
                                        <label for="exposures-default-layout" class="block text-sm font-medium text-gray-700 mb-1.5">
                                            Exposures Default Layout
                                        </label>
                                        <select
                                            id="exposures-default-layout"
                                            value={getFieldValue('exposures.default_layout')}
                                            onchange={(e) => handleNestedFieldChange('exposures.default_layout', e.currentTarget.value)}
                                            disabled={!isDangerZoneEnabled}
                                            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {isDangerZoneEnabled ? '' : 'opacity-50'}"
                                        >
                                            {#each getEnumOptions('exposures.default_layout', ['dashboards-as-rows', 'entities-as-rows']) as value}
                                                <option value={value}>{value}</option>
                                            {/each}
                                        </select>
                                        {#if getFieldMetadata('exposures.default_layout')?.description}
                                            <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('exposures.default_layout')?.description}</p>
                                        {/if}
                                    </div>
                                </div>
                            </div>

                            <!-- Business Events Container (Dimensional Modeling only) -->
                            {#if modelingStyle === 'dimensional_model'}
                            <div class="bg-white border border-amber-200 rounded-lg p-4">
                                <div class="flex items-center gap-2 mb-4">
                                    <h3 class="text-base font-semibold text-amber-900">Business Events</h3>
                                    <Tooltip text="Model business events using BEAM* methodology. Annotate events with dimensions and facts to generate dimensional models. Only available for dimensional modeling style.">
                                        <Icon icon="lucide:help-circle" class="w-4 h-4 text-amber-600 hover:text-amber-700 cursor-help" />
                                    </Tooltip>
                                </div>
                                <div class="space-y-4">
                                    <div class="flex items-center justify-between">
                                        <div class="flex-1">
                                            <div class="flex items-center gap-2">
                                                <label for="business-events-enabled-toggle" class="block text-sm font-medium text-gray-700">
                                                    Business Events Enabled
                                                </label>
                                                {#if isBetaField('business_events.enabled')}
                                                    <span class="px-2 py-0.5 text-xs font-medium bg-amber-200 text-amber-800 rounded">Beta</span>
                                                {/if}
                                            </div>
                                            {#if getFieldMetadata('business_events.enabled')?.description}
                                                <p class="text-xs text-gray-500 mt-1">{getFieldMetadata('business_events.enabled')?.description}</p>
                                            {:else}
                                                <p class="text-xs text-gray-500 mt-1">Enable business events modeling with BEAM* methodology</p>
                                            {/if}
                                        </div>
                                        <label class="relative inline-flex items-center cursor-pointer">
                                            <input
                                                id="business-events-enabled-toggle"
                                                type="checkbox"
                                                checked={getFieldValue('business_events.enabled')}
                                                onchange={(e) => handleNestedFieldChange('business_events.enabled', e.currentTarget.checked)}
                                                disabled={!isDangerZoneEnabled}
                                                class="sr-only peer focus:ring-0 focus:ring-offset-0"
                                            />
                                            <div class="w-11 h-6 bg-gray-200 rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 peer-checked:bg-primary-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full {isDangerZoneEnabled ? '' : 'opacity-50'}"></div>
                                        </label>
                                    </div>

                                    <div>
                                        <label for="business-events-file-input" class="block text-sm font-medium text-gray-700 mb-1.5">
                                            Business Events File
                                        </label>
                                        <input
                                            id="business-events-file-input"
                                            type="text"
                                            value={getFieldValue('business_events.file') || ''}
                                            oninput={(e) => handleNestedFieldChange('business_events.file', e.currentTarget.value || null)}
                                            placeholder="business_events.yml (defaults to same directory as data_model.yml)"
                                            disabled={!isDangerZoneEnabled}
                                            class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {isDangerZoneEnabled ? '' : 'opacity-50'}"
                                        />
                                        {#if getFieldMetadata('business_events.file')?.description}
                                            <p class="mt-1.5 text-xs text-gray-500">{getFieldMetadata('business_events.file')?.description}</p>
                                        {:else}
                                            <p class="mt-1.5 text-xs text-gray-500">Path to business events YAML file (optional, defaults to business_events.yml in data model directory)</p>
                                        {/if}
                                    </div>
                                </div>
                            </div>
                            {/if}
                        </div>
                    </div>

                    {#if fileInfo}
                                <div class="mt-6 text-xs text-gray-500">
                                    <p>Config file: {fileInfo.path}</p>
                                    <p>Last modified: {new Date(fileInfo.mtime * 1000).toLocaleString()}</p>
                                </div>
                            {/if}
                        </form>
            {/if}
        </div>
    </div>

<style>
    @keyframes fade-in {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    :global(.animate-fade-in) {
        animation: fade-in 0.3s ease-out;
    }
</style>
