<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { Node } from "@xyflow/svelte";
    import type { EntityData } from "$lib/types";

    type Props = {
        open: boolean;
        incompleteEntities: Node[];
        onConfirm: () => void;
        onCancel: () => void;
    };

    let { open, incompleteEntities, onConfirm, onCancel }: Props = $props();

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onCancel();
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onCancel();
        }
    }

    function handleConfirm() {
        onConfirm();
    }
</script>

{#if open}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center backdrop-blur-sm"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="warning-modal-title"
    >
        <!-- Modal Content -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
            role="document"
            tabindex="-1"
            aria-label="Warning about incomplete entity descriptions"
        >
            <div class="flex items-start gap-3 mb-4">
                <div class="flex-shrink-0">
                    <Icon icon="lucide:alert-triangle" class="w-6 h-6 text-amber-600" />
                </div>
                <div class="flex-1">
                    <h2 id="warning-modal-title" class="text-lg font-semibold text-gray-900 mb-2">
                        ⚠️ Incomplete Entity Descriptions
                    </h2>
                    <p class="text-sm text-gray-600 mb-4">
                        {incompleteEntities.length} {incompleteEntities.length === 1 ? 'entity is' : 'entities are'} missing descriptions. They will be synced without descriptions.
                    </p>
                </div>
            </div>

            <!-- Entity List -->
            {#if incompleteEntities.length > 0}
                <div class="mb-6 max-h-48 overflow-y-auto border border-gray-200 rounded-md">
                    <ul class="divide-y divide-gray-200">
                        {#each incompleteEntities as entity}
                            {@const data = entity.data as unknown as EntityData}
                            <li class="px-3 py-2 text-sm">
                                <span class="font-medium text-gray-900">{data.label || entity.id}</span>
                                {#if entity.id !== data.label}
                                    <span class="text-gray-500 ml-2">({entity.id})</span>
                                {/if}
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            <!-- Actions -->
            <div class="flex justify-end gap-3">
                <button
                    onclick={onCancel}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                    Cancel
                </button>
                <button
                    onclick={handleConfirm}
                    class="px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded-md hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500"
                >
                    Continue Anyway
                </button>
            </div>
        </div>
    </div>
{/if}

