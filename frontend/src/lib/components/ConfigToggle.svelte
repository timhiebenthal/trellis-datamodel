<script lang="ts">
    import ConfigToggleRow from './config/ConfigToggleRow.svelte';
    import { getConfigFormContext } from '$lib/utils/config-form-context';

    let { path, label, disabled = false }: { path: string; label: string; disabled?: boolean } = $props();

    const form = getConfigFormContext();
    const id = $derived(`${path.replaceAll('.', '-').replaceAll('_', '-')}-toggle`);
</script>

<ConfigToggleRow
    {id}
    {label}
    beta={form.isBetaField(path)}
    description={form.getFieldMetadata(path)?.description}
    checked={!!form.getFieldValue(path)}
    onchange={(checked) => form.handleNestedFieldChange(path, checked)}
    {disabled}
/>
