<script lang="ts">
    import { onMount, untrack } from 'svelte';
    import { getConfig, getConfigSchema, updateConfig, validateConfig, reloadConfig } from '$lib/api';
    import type { ConfigGetResponse, ConfigSchema } from '$lib/api';
    import Icon from '$lib/components/Icon.svelte';
    import FrameworkSection from '$lib/components/config/FrameworkSection.svelte';
    import CanvasSection from '$lib/components/config/CanvasSection.svelte';
    import PathsSection from '$lib/components/config/PathsSection.svelte';
    import EntityGuidanceSection from '$lib/components/config/EntityGuidanceSection.svelte';
    import ModelingSection from '$lib/components/config/ModelingSection.svelte';
    import DangerZoneSection from '$lib/components/config/DangerZoneSection.svelte';
    import { getFieldValue as readFieldValue } from '$lib/utils/config-form';
    import { getFrameworkCopy } from '$lib/utils/framework-display';

    let loading = $state(true);
    let saving = $state(false);
    let error: string | null = $state(null);

    // Config state
    let config: Record<string, any> = $state({});
    let schema: ConfigSchema = $state({ fields: {}, beta_flags: [] });
    let fileInfo: { path: string; mtime: number; hash: string } | null = $state(null);
    let trellisVersion: string | null = $state(null);

    // Form validation state
    let validationErrors: Record<string, string> = $state({});
    let showValidationSummary = $state(false);

    // Danger Zone acknowledgment
    let dangerZoneAcknowledged = $state(false);

    // Conflict state
    let conflictWarning: string | null = $state(null);
    let conflictInfo: any = $state(null);

    // Reactive modeling style for conditional rendering
    let modelingStyle = $derived(config.modeling_style);

    // Entity guidance toggle state for dependent fields
    let entityGuidanceEnabled = $derived(!!config?.entity_creation_guidance?.enabled);
    // Re-runs only when entityGuidanceEnabled changes (as the old `$:` block did):
    // the config read/write inside is untracked.
    $effect(() => {
        if (!entityGuidanceEnabled) {
            untrack(() => {
                if (getFieldValue('entity_creation_guidance.push_warning_enabled')) {
                    handleNestedFieldChange('entity_creation_guidance.push_warning_enabled', false);
                }
            });
        }
    });

    let selectedFramework = $derived(config.framework || 'dbt-core');
    let frameworkCopy = $derived(getFrameworkCopy(selectedFramework));

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
            trellisVersion = response.trellis_version ?? null;

            // Ensure defaults when schema metadata is missing
            if (!schema?.fields || Object.keys(schema.fields).length === 0) {
                schema = {
                    fields: {
                        framework: {
                            type: 'enum',
                            enum_values: ['dbt-core', 'bruin'],
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
        return readFieldValue(config, path);
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
                    <FrameworkSection {config} {schema} onChange={handleFieldChange} />

                    <CanvasSection {config} onChange={handleFieldChange} onNestedChange={handleNestedFieldChange} />

                    <PathsSection
                        {config}
                        {schema}
                        {selectedFramework}
                        {validationErrors}
                        onChange={handleFieldChange}
                    />

                    <EntityGuidanceSection
                        {config}
                        {schema}
                        onNestedChange={handleNestedFieldChange}
                        pushWarningDescription={frameworkCopy.pushWarningDescription}
                    />

                    <ModelingSection {config} {schema} {modelingStyle} onNestedChange={handleNestedFieldChange} />

                    <DangerZoneSection
                        {config}
                        {schema}
                        onNestedChange={handleNestedFieldChange}
                        lineageTooltip={frameworkCopy.lineageTooltip}
                        bind:acknowledged={dangerZoneAcknowledged}
                    />

                    {#if fileInfo}
                                <div class="mt-6 text-xs text-gray-500">
                                    <p>Config file: {fileInfo.path}</p>
                                    <p>Last modified: {new Date(fileInfo.mtime * 1000).toISOString()}</p>
                                    <p>trellis version: {trellisVersion ?? 'Unknown'}</p>
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
