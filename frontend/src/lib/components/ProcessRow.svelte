<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { BusinessEventProcess } from "$lib/types";

    type Props = {
        process: BusinessEventProcess;
        eventCount: number;
        onAnnotate?: () => void;
        onEdit?: () => void;
        onOpenCanvas?: () => void;
        onResolve?: (processId: string) => Promise<void> | void;
    };

    let { process, eventCount, onAnnotate, onEdit, onOpenCanvas, onResolve }: Props = $props();

    let resolving = $state(false);

    async function handleResolve() {
        if (!onResolve || resolving) return;
        resolving = true;
        try {
            const result = onResolve(process.id);
            if (result instanceof Promise) {
                await result;
            }
        } finally {
            resolving = false;
        }
    }
</script>

<div class="bg-gray-50 border-b border-gray-200 px-4 py-3 flex items-center justify-between gap-4" role="group">
    <div class="flex-1 flex items-center gap-3 min-w-0">
        <div class="flex flex-col min-w-0">
            <span class="text-sm font-semibold text-slate-800 truncate">
                {process.name}
            </span>
            <span class="text-xs font-medium text-slate-600 uppercase tracking-wide">
                Process of {eventCount} event{eventCount === 1 ? "" : "s"}
            </span>
            <div class="flex items-center gap-2 text-[11px] text-slate-500">
                <span>{process.type}</span>
            </div>
        </div>
    </div>
    <div class="flex items-center gap-1">
        <button
            type="button"
            class="p-1.5 rounded text-gray-600 hover:text-green-600 hover:bg-green-50 transition-colors disabled:text-gray-300 disabled:hover:bg-transparent disabled:cursor-not-allowed"
            on:click={() => onEdit?.()}
            disabled={!onEdit}
            title="Edit process details"
        >
            <Icon icon="lucide:edit" class="w-4 h-4" />
        </button>
        <button
            type="button"
            class="p-1.5 rounded text-gray-600 hover:text-green-600 hover:bg-green-50 transition-colors disabled:text-gray-300 disabled:hover:bg-transparent disabled:cursor-not-allowed"
            on:click={() => onAnnotate?.()}
            disabled={!onAnnotate}
            title="Annotate process"
        >
            <Icon icon="lucide:highlighter" class="w-4 h-4" />
        </button>
        <button
            type="button"
            class="p-1.5 rounded text-gray-600 hover:text-blue-600 hover:bg-blue-50 transition-colors disabled:text-gray-300 disabled:hover:bg-transparent disabled:cursor-not-allowed"
            on:click={() => onOpenCanvas?.()}
            disabled={!onOpenCanvas}
            title="Open process on canvas"
        >
            <Icon icon="lucide:layout-dashboard" class="w-4 h-4" />
        </button>
        <button
            type="button"
            class="p-1.5 rounded text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors disabled:text-gray-300 disabled:hover:bg-transparent disabled:cursor-not-allowed"
            on:click={handleResolve}
            disabled={!onResolve || resolving}
            title="Resolve process"
        >
            <Icon icon="lucide:x" class="w-4 h-4" />
        </button>
    </div>
</div>
