<script lang="ts">
    // Presentational: label, beta badge and switch from props. For a field addressed by
    // config path, use the context-bound ConfigToggle.
    import ConfigToggleSwitch from './ConfigToggleSwitch.svelte';

    let {
        id,
        label,
        checked,
        onchange,
        disabled,
        beta = false,
        description = null,
    }: {
        id: string;
        label: string;
        checked: boolean;
        onchange: (checked: boolean) => void;
        disabled: boolean;
        beta?: boolean;
        description?: string | null;
    } = $props();
</script>

<div class="flex items-center justify-between">
    <div class="flex-1">
        <div class="flex items-center gap-2">
            <label for={id} class="block text-sm font-medium text-gray-700">
                {label}
            </label>
            {#if beta}
                <span class="px-2 py-0.5 text-xs font-medium bg-amber-200 text-amber-800 rounded">Beta</span>
            {/if}
        </div>
        {#if description}
            <p class="text-xs text-gray-500 mt-1">{description}</p>
        {/if}
    </div>
    <ConfigToggleSwitch {id} {checked} {onchange} {disabled} />
</div>
