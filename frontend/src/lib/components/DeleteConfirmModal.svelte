<script lang="ts">
    type Props = {
        open: boolean;
        entityLabel: string;
        onConfirm: () => void;
        onCancel: () => void;
    };

    let { open, entityLabel, onConfirm, onCancel }: Props = $props();

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
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
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
            role="document"
            tabindex="-1"
        >
            <h2 id="delete-modal-title" class="text-lg font-semibold text-gray-900 mb-2">
                Delete Entity?
            </h2>
            <p class="text-sm text-gray-600 mb-6">
                Are you sure you want to delete <span class="font-medium">'{entityLabel}'</span>? 
                This will also remove all relationships connected to this entity.
            </p>
            <div class="flex justify-end gap-3">
                <button
                    onclick={onCancel}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                    Cancel
                </button>
                <button
                    onclick={handleConfirm}
                    class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                    Delete
                </button>
            </div>
        </div>
    </div>
{/if}

