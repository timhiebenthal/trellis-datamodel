<script lang="ts">
    import Modal from "./Modal.svelte";

    type Props = {
        open: boolean;
        entityLabel: string;
        entityCount: number;
        onConfirm: () => void;
        onCancel: () => void;
    };

    let { open, entityLabel, entityCount, onConfirm, onCancel }: Props = $props();

    function handleConfirm() {
        onConfirm();
    }
</script>

<Modal
    {open}
    onClose={onCancel}
    size="lg"
    class="bg-white rounded-lg shadow-xl p-8 w-full mx-4"
    labelledBy="delete-modal-title"
>
    <h2 id="delete-modal-title" class="text-xl font-semibold text-gray-900 mb-3">
        Delete Entity?
    </h2>
    <p class="text-sm text-gray-600 mb-8">
        {#if entityCount > 1}
            Are you sure you want to delete <span class="font-medium">these {entityCount} entities</span>?
            This will also remove all relationships connected to them.
        {:else}
            Are you sure you want to delete <span class="font-medium">'{entityLabel}'</span>?
            This will also remove all relationships connected to this entity.
        {/if}
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
</Modal>

