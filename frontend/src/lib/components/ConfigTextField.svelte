<script lang="ts">
    import ConfigTextInput from './config/ConfigTextInput.svelte';
    import { getConfigFormContext } from '$lib/utils/config-form-context';

    let {
        path,
        label,
        disabled = false,
        placeholder = undefined,
    }: { path: string; label: string; disabled?: boolean; placeholder?: string } = $props();

    const form = getConfigFormContext();
    const id = $derived(`${path.replaceAll('.', '-').replaceAll('_', '-')}-input`);
</script>

<ConfigTextInput
    {id}
    {label}
    value={form.getFieldValue(path) ?? ''}
    oninput={(value) => form.handleNestedFieldChange(path, value)}
    {placeholder}
    description={form.getFieldMetadata(path)?.description}
    {disabled}
/>
