<script lang="ts">
    let {
        id,
        label,
        value,
        options,
        onchange,
        description = null,
        disabled = false,
    }: {
        id: string;
        label: string;
        value: any;
        options: string[];
        onchange: (value: string) => void;
        description?: string | null;
        disabled?: boolean;
    } = $props();
</script>

<div>
    <label for={id} class="block text-sm font-medium text-gray-700 mb-1.5">
        {label}
    </label>
    <select
        {id}
        {value}
        onchange={(e) => onchange(e.currentTarget.value)}
        {disabled}
        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {disabled ? 'opacity-50' : ''}"
    >
        {#each options as option}
            <option value={option}>{option}</option>
        {/each}
    </select>
    {#if description}
        <p class="mt-1.5 text-xs text-gray-500">{description}</p>
    {/if}
</div>
