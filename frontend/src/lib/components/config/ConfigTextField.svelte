<script lang="ts">
    import type { Snippet } from 'svelte';

    let {
        id,
        label,
        value,
        oninput,
        placeholder = undefined,
        description = null,
        error = null,
        mono = true,
        type = 'text',
        min = undefined,
        disabled = false,
        children,
    }: {
        id: string;
        label: string;
        value: any;
        oninput: (value: string) => void;
        placeholder?: string;
        description?: string | null;
        error?: string | null;
        mono?: boolean;
        type?: string;
        min?: string;
        disabled?: boolean;
        /** Rich help text; replaces `description` when given. */
        children?: Snippet;
    } = $props();
</script>

<div>
    <label for={id} class="block text-sm font-medium text-gray-700 mb-1.5">
        {label}
    </label>
    <input
        {id}
        {type}
        {min}
        {value}
        oninput={(e) => oninput(e.currentTarget.value)}
        {placeholder}
        {disabled}
        class="w-full px-3 py-2 text-sm {mono ? 'font-mono ' : ''}border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:outline-none transition-all duration-200 shadow-sm {error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''} {disabled ? 'opacity-50' : ''}"
    />
    {#if children}
        <p class="mt-1.5 text-xs text-gray-500">{@render children()}</p>
    {:else if description}
        <p class="mt-1.5 text-xs text-gray-500">{description}</p>
    {/if}
    {#if error}
        <p class="mt-1 text-xs text-red-600">{error}</p>
    {/if}
</div>
