<script lang="ts">
    let {
        label,
        name,
        plural,
        idPrefix,
        values,
        available,
        onChange,
    }: {
        /** Field label, e.g. "Default Domains" */
        label: string;
        /** Singular display name, e.g. "Domain" */
        name: string;
        /** Lowercase plural used in hints, e.g. "domains" */
        plural: string;
        idPrefix: string;
        values: string[];
        available: string[];
        onChange: (values: string[]) => void;
    } = $props();

    let canAdd = $derived(available.some((value) => !values.includes(value)));

    function addNext() {
        const nextValue = available.find((value) => !values.includes(value));
        if (nextValue) onChange([...values, nextValue]);
    }
</script>

<div>
    <label for="{idPrefix}-0" class="block text-sm font-medium text-gray-700 mb-1.5">
        {label}
    </label>
    {#each values as value, index (index)}
        <div class="flex items-center gap-2 mb-2">
            <select
                id={`${idPrefix}-${index}`}
                {value}
                aria-label={`Canvas Default ${name} ${index + 1}`}
                onchange={(e) => {
                    const newValues = [...values];
                    newValues[index] = e.currentTarget.value;
                    onChange(newValues);
                }}
                class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm"
            >
                {#if value && !available.includes(value)}
                    <option {value} disabled>{value} (not available)</option>
                {/if}
                {#each available as option}
                    <option value={option}>{option}</option>
                {/each}
            </select>
            <button
                type="button"
                aria-label={`Remove ${name} ${index + 1}`}
                onclick={() => {
                    const newValues = [...values];
                    newValues.splice(index, 1);
                    onChange(newValues);
                }}
                class="px-3 py-2 text-red-600 hover:bg-red-50 border border-red-300 rounded-md text-lg font-medium"
            >
                ×
            </button>
        </div>
    {/each}
    {#if values.length === 0}
        <p class="mt-1.5 text-xs text-gray-500">Empty = all {plural} included</p>
    {/if}
    {#if available.length === 0}
        <p class="mt-1.5 text-xs text-gray-500">No {plural} are available from the current Canvas entities.</p>
    {/if}
    <button
        type="button"
        onclick={addNext}
        disabled={!canAdd}
        class="mt-2 px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 border border-primary-300 rounded-md"
    >
        + Add {name}
    </button>
</div>
