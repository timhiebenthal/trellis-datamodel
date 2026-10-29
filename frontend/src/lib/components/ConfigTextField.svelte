<script lang="ts">
    import { getConfigFormContext } from '$lib/utils/config-form-context';

    let {
        path,
        label,
        disabled = false,
        placeholder = undefined,
    }: { path: string; label: string; disabled?: boolean; placeholder?: string } = $props();

    const form = getConfigFormContext();
    const id = $derived(`${path.replaceAll('.', '-').replaceAll('_', '-')}-input`);
    const description = $derived(form.getFieldMetadata(path)?.description);
</script>

<div>
    <label for={id} class="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
    <input
        {id}
        type="text"
        value={form.getFieldValue(path) ?? ''}
        oninput={(e) => form.handleNestedFieldChange(path, e.currentTarget.value)}
        {placeholder}
        {disabled}
        class="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {disabled ? 'opacity-50' : ''}"
    />
    {#if description}
        <p class="mt-1.5 text-xs text-gray-500">{description}</p>
    {/if}
</div>
