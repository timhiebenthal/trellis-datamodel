<script lang="ts">
    import Icon from "@iconify/svelte";
    import EventAnnotator from "./EventAnnotator.svelte";
    import type { BusinessEvent } from "$lib/types";

    type Props = {
        open: boolean;
        event: BusinessEvent | null;
        onSave: () => void;
        onCancel: () => void;
    };

    let { open, event, onSave, onCancel }: Props = $props();

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

    function handleSave(updatedEvent: BusinessEvent) {
        onSave();
    }
</script>

{#if open && event}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center backdrop-blur-sm"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="annotate-modal-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            role="document"
            tabindex="-1"
        >
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h2 id="annotate-modal-title" class="text-xl font-semibold text-gray-900">
                        Annotate Event
                    </h2>
                    <p class="text-sm text-gray-600 mt-1">
                        {event.text}
                    </p>
                </div>
                <button
                    class="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                    onclick={onCancel}
                    aria-label="Close"
                >
                    <Icon icon="lucide:x" class="w-5 h-5" />
                </button>
            </div>

            <!-- Event Annotator -->
            <EventAnnotator
                {event}
                onSave={handleSave}
                onCancel={onCancel}
            />
        </div>
    </div>
{/if}
