<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { BusinessEvent } from "$lib/types";
    import { deleteBusinessEvent } from "$lib/api";
    import DomainBadge from "./DomainBadge.svelte";

    type Props = {
        event: BusinessEvent;
        onEditSevenWs: (event: BusinessEvent) => void;
        onGenerateEntities: (event: BusinessEvent) => void;
        onDelete: () => void;
        onViewSevenWs?: (event: BusinessEvent) => void;
    };

    let { event, onEditSevenWs, onGenerateEntities, onDelete, onViewSevenWs }: Props = $props();

    let showDeleteConfirm = $state(false);

    // Annotations calculation
    const annotations = $derived(event.annotations || {
        who: [],
        what: [],
        when: [],
        where: [],
        how: [],
        how_many: [],
        why: []
    });

    const annotationsFilledCount = $derived(
        Object.values(annotations).filter((entries) => entries.length > 0).length
    );

    const annotationsBadgeColor = $derived(() => {
        if (annotationsFilledCount === 0) {
            return "bg-gray-100 text-gray-700 border-gray-300";
        } else if (annotationsFilledCount === 7) {
            return "bg-green-100 text-green-800 border-green-300";
        } else {
            return "bg-amber-100 text-amber-800 border-amber-300";
        }
    });

    const hasHowManyEntries = $derived(annotations.how_many.length > 0);

    // Check if Generate Entities button should be enabled (based on annotations only)
    const hasDimensionEntries = $derived(
        annotations.who.length > 0 || 
        annotations.what.length > 0 || 
        annotations.when.length > 0 || 
        annotations.where.length > 0 || 
        annotations.how.length > 0 || 
        annotations.why.length > 0
    );
    const canGenerateEntities = $derived(hasDimensionEntries && hasHowManyEntries);
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
    class="border-b border-gray-200 bg-white hover:bg-gray-50 transition-colors duration-150 py-3 px-4"
>
    <!-- List-like row layout -->
    <div class="flex items-center gap-4">
        <!-- Event text (flex-1 to take available space) -->
        <div class="flex-1 min-w-0 text-sm text-gray-700 leading-relaxed">
            {event.text}
        </div>

        <!-- Status badges -->
        <div class="flex items-center gap-2 flex-shrink-0">
            {#if annotationsFilledCount > 0}
                <span
                    class="px-2 py-1 rounded text-xs font-medium border {annotationsBadgeColor()} flex items-center gap-1"
                    title="Annotations completion status"
                >
                    {annotationsFilledCount}/7
                    {#if !hasHowManyEntries}
                        <span title="No 'How Many' entries - fact table incomplete" class="inline-flex items-center">
                            <Icon icon="lucide:alert-triangle" class="w-3 h-3 text-amber-600" />
                        </span>
                    {/if}
                </span>
            {/if}
            {#if hasDerivedEntities}
                <span
                    class="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800 border border-green-300 flex items-center gap-1"
                    title="Entities have been generated from this event"
                >
                    <Icon icon="lucide:check-circle" class="w-3 h-3" />
                    Generated
                </span>
            {/if}
        </div>

        <!-- Domain and Type badges -->
        <div class="flex items-center gap-2 flex-shrink-0">
            {#if event.domain}
                <DomainBadge domain={event.domain} size="small" />
            {/if}
            <span
                class="px-2 py-1 rounded text-xs font-medium border {typeBadgeClass}"
            >
                {event.type}
            </span>
        </div>

        <!-- Action buttons -->
        <div class="flex items-center gap-1 flex-shrink-0">
            {#if annotationsFilledCount > 0 && onViewSevenWs}
                <button
                    onclick={() => onViewSevenWs(event)}
                    class="p-1.5 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                    title="View annotations"
                >
                    <Icon icon="lucide:list" class="w-4 h-4" />
                </button>
            {/if}

            <button
                onclick={() => onEditSevenWs(event)}
                class="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title={annotationsFilledCount > 0 ? "Edit annotations" : "Add annotations (Who, What, When, Where, How, How Many, Why)"}
            >
                <Icon icon="lucide:highlighter" class="w-4 h-4" />
            </button>

            <button
                onclick={() => onGenerateEntities(event)}
                disabled={!canGenerateEntities}
                class="p-1.5 rounded transition-colors"
                class:text-blue-600={canGenerateEntities}
                class:hover:text-blue-700={canGenerateEntities}
                class:hover:bg-blue-50={canGenerateEntities}
                class:text-gray-400={!canGenerateEntities}
                class:cursor-not-allowed={!canGenerateEntities}
                class:cursor-pointer={canGenerateEntities}
                title={
                    canGenerateEntities
                        ? "Generate dimensional entities from annotations"
                        : !hasHowManyEntries
                            ? "Add 'How Many' entries to generate fact table"
                            : "Add dimension entries (Who, What, When, Where, How, or Why) to generate entities"
                }
            >
                <Icon icon="lucide:sparkles" class="w-4 h-4" />
            </button>

            <button
                onclick={handleDelete}
                class="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                title="Delete this event"
            >
                <Icon icon="lucide:trash-2" class="w-4 h-4" />
            </button>
        </div>
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
