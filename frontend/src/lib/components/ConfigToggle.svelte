<script lang="ts">
    import { getConfigFormContext } from '$lib/utils/config-form-context';

    let { path, label, disabled = false }: { path: string; label: string; disabled?: boolean } = $props();

    const form = getConfigFormContext();
    const id = $derived(`${path.replaceAll('.', '-').replaceAll('_', '-')}-toggle`);
    const description = $derived(form.getFieldMetadata(path)?.description);
</script>

<div class="flex items-center justify-between">
    <div class="flex-1">
        <div class="flex items-center gap-2">
            <label for={id} class="block text-sm font-medium text-gray-700">{label}</label>
            {#if form.isBetaField(path)}
                <span class="px-2 py-0.5 text-xs font-medium bg-amber-200 text-amber-800 rounded">Beta</span>
            {/if}
        </div>
        {#if description}
            <p class="text-xs text-gray-500 mt-1">{description}</p>
        {/if}
    </div>
    <label class="relative inline-flex items-center cursor-pointer">
        <input
            {id}
            type="checkbox"
            checked={!!form.getFieldValue(path)}
            onchange={(e) => form.handleNestedFieldChange(path, e.currentTarget.checked)}
            {disabled}
            class="sr-only peer focus:ring-0 focus:ring-offset-0"
        />
        <div class="w-11 h-6 bg-gray-200 rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 peer-checked:bg-primary-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full {disabled ? 'opacity-50' : ''}"></div>
    </label>
</div>
