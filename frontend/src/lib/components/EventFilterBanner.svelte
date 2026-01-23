<script lang="ts">
    import Icon from "$lib/components/Icon.svelte";
    import { onMount, onDestroy } from "svelte";

    type Props = {
        eventText: string;
        entityCount: number;
        onClear: () => void;
    };

    let { eventText, entityCount, onClear }: Props = $props();

    // Handle Escape key to clear filter
    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onClear();
        }
    }

    onMount(() => {
        window.addEventListener("keydown", handleKeydown);
    });

    onDestroy(() => {
        window.removeEventListener("keydown", handleKeydown);
    });
</script>

<div
    class="fixed top-20 left-1/2 -translate-x-1/2 z-40 bg-blue-50 text-blue-800 border border-blue-200 rounded-lg shadow-lg px-4 py-3 flex items-center gap-3 max-w-[90vw] sm:max-w-none animate-in fade-in slide-in-from-top-2 duration-300"
    role="status"
    aria-live="polite"
    aria-label="Canvas filtered by business event"
>
    <!-- Filter info -->
    <div class="flex items-center gap-2 text-sm flex-wrap">
        <Icon icon="lucide:filter" class="w-4 h-4 flex-shrink-0" />
        <span class="font-medium">Filtered by event:</span>
        <span class="italic break-words">'{eventText}'</span>
        <span class="text-blue-600 hidden sm:inline">•</span>
        <span class="w-full sm:w-auto">Showing {entityCount} {entityCount === 1 ? 'entity' : 'entities'}</span>
    </div>

    <!-- Clear filter button -->
    <button
        onclick={onClear}
        class="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        title="Clear filter (Esc)"
        aria-label="Clear filter and show all entities"
    >
        <Icon icon="lucide:x" class="w-4 h-4" />
    </button>
</div>
