<script lang="ts">
    // Test-only harness for ConfigFields.test.ts: the field components read the
    // config page's helpers from context, so they need a provider around them.
    import ConfigToggle from './ConfigToggle.svelte';
    import ConfigTextField from './ConfigTextField.svelte';
    import { setConfigFormContext } from '$lib/utils/config-form-context';

    type Props = {
        initial?: Record<string, any>;
        onConfig?: (config: Record<string, any>) => void;
        disabled?: boolean;
    };

    let { initial = {}, onConfig = () => {}, disabled = false }: Props = $props();

    let config: Record<string, any> = $state({ ...initial });

    const fields: Record<string, { description: string }> = {
        'ossie.enabled': { description: 'Enable Ossie export' },
        'ossie.source.database': { description: 'Database segment' },
    };

    function getFieldValue(path: string) {
        let current: any = config;
        for (const part of path.split('.')) {
            if (current && current[part] !== undefined) current = current[part];
            else return null;
        }
        return current;
    }

    function handleNestedFieldChange(path: string, value: any) {
        const parts = path.split('.');
        const next: any = { ...config };
        let current = next;
        for (const part of parts.slice(0, -1)) {
            current[part] = { ...(current[part] ?? {}) };
            current = current[part];
        }
        current[parts[parts.length - 1]] = value;
        config = next;
        onConfig(next);
    }

    setConfigFormContext({
        getFieldValue,
        handleNestedFieldChange,
        getFieldMetadata: (path) => (fields[path] as any) ?? null,
        isBetaField: (path) => path === 'ossie.enabled',
    });
</script>

<ConfigToggle path="ossie.enabled" label="Ossie Export Enabled" {disabled} />
<ConfigTextField path="ossie.source.database" label="Database Override" {disabled} />
