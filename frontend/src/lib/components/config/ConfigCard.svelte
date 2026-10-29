<script lang="ts">
    import type { Snippet } from 'svelte';
    import Icon from '$lib/components/Icon.svelte';
    import Tooltip from '$lib/components/Tooltip.svelte';

    let {
        title,
        tooltip,
        headerClass = 'mb-4',
        children,
    }: { title: string; tooltip: string; headerClass?: string; children: Snippet } = $props();
</script>

<div class="bg-white border border-gray-200 rounded-lg p-6">
    <div class="flex items-center gap-2 {headerClass}">
        <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
        <Tooltip text={tooltip}>
            <Icon icon="lucide:help-circle" class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
        </Tooltip>
    </div>
    {@render children()}
</div>
