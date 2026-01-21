<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { BusinessEvent } from "$lib/types";
    import { deleteBusinessEvent } from "$lib/api";

    type Props = {
        event: BusinessEvent;
        onAnnotate: (event: BusinessEvent) => void;
        onGenerateEntities: (event: BusinessEvent) => void;
        onEdit: (event: BusinessEvent) => void;
        onDelete: () => void;
    };

    let { event, onAnnotate, onGenerateEntities, onEdit, onDelete }: Props = $props();

    let showDeleteConfirm = $state(false);

    // Check if Generate Entities button should be enabled
    const hasAnnotations = $derived(event.annotations.length > 0);
    const hasDimensions = $derived(event.annotations.some((a) => a.type === "dimension"));
    const hasFacts = $derived(event.annotations.some((a) => a.type === "fact"));
    const canGenerateEntities = $derived(hasAnnotations && hasDimensions && hasFacts);
    const hasDerivedEntities = $derived(event.derived_entities.length > 0);

    // Type badge colors
    const typeBadgeClass = $derived(() => {
        switch (event.type) {
            case "discrete":
                return "bg-blue-100 text-blue-800 border-blue-300";
            case "evolving":
                return "bg-yellow-100 text-yellow-800 border-yellow-300";
            case "recurring":
                return "bg-purple-100 text-purple-800 border-purple-300";
            default:
                return "bg-gray-100 text-gray-800 border-gray-300";
        }
    });

    // Render event text with highlighted annotations
    function renderAnnotatedText(): Array<{ text: string; type?: "dimension" | "fact" }> {
        if (event.annotations.length === 0) {
            return [{ text: event.text }];
        }

        // Sort annotations by start position
        const sortedAnnotations = [...event.annotations].sort((a, b) => a.start_pos - b.start_pos);
        const parts: Array<{ text: string; type?: "dimension" | "fact" }> = [];
        let lastPos = 0;

        for (const ann of sortedAnnotations) {
            // Add text before annotation
            if (ann.start_pos > lastPos) {
                parts.push({ text: event.text.slice(lastPos, ann.start_pos) });
            }
            // Add annotated text
            parts.push({
                text: event.text.slice(ann.start_pos, ann.end_pos),
                type: ann.type,
            });
            lastPos = ann.end_pos;
        }

        // Add remaining text after last annotation
        if (lastPos < event.text.length) {
            parts.push({ text: event.text.slice(lastPos) });
        }

        return parts;
    }

    function handleDelete() {
        showDeleteConfirm = true;
    }

    function handleDeleteConfirm() {
        deleteBusinessEvent(event.id)
            .then(() => {
                showDeleteConfirm = false;
                onDelete();
            })
            .catch((error) => {
                console.error("Error deleting event:", error);
                alert(`Failed to delete event: ${error.message}`);
            });
    }

    function handleDeleteCancel() {
        showDeleteConfirm = false;
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            handleDeleteCancel();
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            handleDeleteCancel();
        }
    }
</script>

<div
    class="rounded-lg border border-gray-300 bg-white shadow-sm hover:shadow-md transition-all duration-200 p-4"
>
    <!-- Header with type badge -->
    <div class="flex items-start justify-between mb-3">
        <div class="flex items-center gap-2 flex-1 min-w-0">
            <span
                class="px-2 py-1 rounded text-xs font-medium border {typeBadgeClass}"
            >
                {event.type}
            </span>
            {#if hasDerivedEntities}
                <span
                    class="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800 border border-green-300 flex items-center gap-1"
                    title="Entities have been generated from this event"
                >
                    <Icon icon="lucide:check-circle" class="w-3 h-3" />
                    Entities Generated
                </span>
            {/if}
        </div>
    </div>

    <!-- Event text with annotations -->
    <div class="mb-4 text-sm text-gray-700 leading-relaxed">
        {#each renderAnnotatedText() as part}
            {#if part.type === "dimension"}
                <span
                    class="bg-blue-200 text-blue-900 px-1 rounded font-medium"
                    title="Dimension: {part.text}"
                >
                    {part.text}
                </span>
            {:else if part.type === "fact"}
                <span
                    class="bg-green-200 text-green-900 px-1 rounded font-medium"
                    title="Fact: {part.text}"
                >
                    {part.text}
                </span>
            {:else}
                {part.text}
            {/if}
        {/each}
    </div>

    <!-- Action buttons -->
    <div class="flex flex-wrap gap-2 pt-3 border-t border-gray-200">
        <button
            onclick={() => onAnnotate(event)}
            class="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500 flex items-center gap-1.5"
            title="Annotate text segments as dimensions or facts"
        >
            <Icon icon="lucide:tag" class="w-3.5 h-3.5" />
            Annotate
        </button>

        <button
            onclick={() => onGenerateEntities(event)}
            disabled={!canGenerateEntities}
            class="px-3 py-1.5 text-xs font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500 flex items-center gap-1.5 transition-all"
            class:text-white={canGenerateEntities}
            class:bg-blue-600={canGenerateEntities}
            class:hover:bg-blue-700={canGenerateEntities}
            class:text-gray-400={!canGenerateEntities}
            class:bg-gray-100={!canGenerateEntities}
            class:cursor-not-allowed={!canGenerateEntities}
            class:cursor-pointer={canGenerateEntities}
            title={
                canGenerateEntities
                    ? "Generate dimensional entities from annotations"
                    : "Add at least one dimension and one fact annotation to generate entities"
            }
        >
            <Icon icon="lucide:sparkles" class="w-3.5 h-3.5" />
            Generate Entities
        </button>

        <button
            onclick={() => onEdit(event)}
            class="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500 flex items-center gap-1.5"
            title="Edit event text or type"
        >
            <Icon icon="lucide:pencil" class="w-3.5 h-3.5" />
            Edit
        </button>

        <button
            onclick={handleDelete}
            class="px-3 py-1.5 text-xs font-medium text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-red-500 flex items-center gap-1.5"
            title="Delete this event"
        >
            <Icon icon="lucide:trash-2" class="w-3.5 h-3.5" />
            Delete
        </button>
    </div>
</div>

<!-- Delete Confirmation Modal -->
{#if showDeleteConfirm}
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="delete-event-modal-title"
    >
        <div
            class="bg-white rounded-lg shadow-xl p-8 max-w-lg w-full mx-4"
            role="document"
            tabindex="-1"
        >
            <h2 id="delete-event-modal-title" class="text-xl font-semibold text-gray-900 mb-3">
                Delete Business Event?
            </h2>
            <p class="text-sm text-gray-600 mb-8">
                Are you sure you want to delete this business event? This action cannot be undone.
            </p>
            <div class="flex justify-end gap-3">
                <button
                    onclick={handleDeleteCancel}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                    Cancel
                </button>
                <button
                    onclick={handleDeleteConfirm}
                    class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                    Delete
                </button>
            </div>
        </div>
    </div>
{/if}
