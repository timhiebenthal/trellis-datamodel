<script lang="ts">
    import type { Snippet } from 'svelte';
    import Icon from '$lib/components/Icon.svelte';
    import Tooltip from '$lib/components/Tooltip.svelte';

    let { title, tooltip, children }: { title: string; tooltip: string; children: Snippet } = $props();
</script>

<div class="bg-white border border-amber-200 rounded-lg p-4">
    <div class="flex items-center gap-2 mb-4">
        <h3 class="text-base font-semibold text-amber-900">{title}</h3>
        <Tooltip text={tooltip}>
            <Icon icon="lucide:help-circle" class="w-4 h-4 text-amber-600 hover:text-amber-700 cursor-help" />
        </Tooltip>
    </div>
    <div class="space-y-4">
        {@render children()}
    </div>
</div>
