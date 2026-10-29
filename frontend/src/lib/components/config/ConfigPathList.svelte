<script lang="ts">
    let {
        idPrefix,
        label,
        values,
        placeholder,
        emptyText,
        onChange,
    }: {
        idPrefix: string;
        label: string;
        values: string[];
        placeholder: string;
        emptyText: string;
        onChange: (values: string[]) => void;
    } = $props();
</script>

<div>
    <label for="{idPrefix}-0" class="block text-sm font-medium text-gray-700 mb-1.5">
        {label}
    </label>
    {#each values as path, index (index)}
        <div class="flex items-center gap-2 mb-2">
            <input
                id={`${idPrefix}-${index}`}
                type="text"
                value={path}
                oninput={(e) => {
                    const newPaths = [...values];
                    newPaths[index] = e.currentTarget.value;
                    onChange(newPaths);
                }}
                {placeholder}
                class="flex-1 px-3 py-2 text-sm font-mono border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
            />
            <button
                type="button"
                onclick={() => {
                    const newPaths = [...values];
                    newPaths.splice(index, 1);
                    onChange(newPaths);
                }}
                class="px-3 py-2 text-red-600 hover:bg-red-50 border border-red-300 rounded-md text-lg font-medium"
                title="Remove path"
            >
                ×
            </button>
        </div>
    {/each}
    {#if values.length === 0}
        <p class="mt-1.5 text-xs text-gray-500">{emptyText}</p>
    {/if}
    <button
        type="button"
        onclick={() => onChange([...values, ''])}
        class="mt-2 px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 border border-primary-300 rounded-md"
    >
        + Add Path
    </button>
</div>
