<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { BusinessEvent } from "$lib/types";
    import { deleteBusinessEvent } from "$lib/api";
    import DomainBadge from "./DomainBadge.svelte";

    type Props = {
        event: BusinessEvent;
        onAnnotate: (event: BusinessEvent) => void;
        onGenerateEntities: (event: BusinessEvent) => void;
        onEdit: (event: BusinessEvent) => void;
        onDelete: () => void;
        onViewSevenWs?: (event: BusinessEvent) => void;
    };

    let { event, onAnnotate, onGenerateEntities, onEdit, onDelete, onViewSevenWs }: Props = $props();

    let showDeleteConfirm = $state(false);

    // 7 Ws calculation
    const sevenWs = $derived(event.seven_ws || {
        who: [],
        what: [],
        when: [],
        where: [],
        how: [],
        how_many: [],
        why: []
    });

    const sevenWsFilledCount = $derived(
        Object.values(sevenWs).filter((entries) => entries.length > 0).length
    );

    const sevenWsBadgeColor = $derived(() => {
        if (sevenWsFilledCount === 0) {
            return "bg-gray-100 text-gray-700 border-gray-300";
        } else if (sevenWsFilledCount === 7) {
            return "bg-green-100 text-green-800 border-green-300";
        } else {
            return "bg-amber-100 text-amber-800 border-amber-300";
        }
    });

    const hasHowManyEntries = $derived(sevenWs.how_many.length > 0);

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

    // Render event text with highlighted annotations (only if using legacy annotations)
    function renderAnnotatedText(): Array<{ text: string; type?: "dimension" | "fact" }> {
        // If 7 Ws data exists, show plain text (concise display)
        if (event.seven_ws && Object.keys(event.seven_ws).some(key => event.seven_ws![key as keyof typeof event.seven_ws].length > 0)) {
            return [{ text: event.text }];
        }
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
    class="border-b border-gray-200 bg-white hover:bg-gray-50 transition-colors duration-150 py-3 px-4"
>
    <!-- List-like row layout -->
    <div class="flex items-center gap-4">
        <!-- Event text with annotations (flex-1 to take available space) -->
        <div class="flex-1 min-w-0 text-sm text-gray-700 leading-relaxed">
            {#each renderAnnotatedText() as part}
            {#if part.type === "dimension"}
                <span
                    class="bg-green-200 text-green-900 px-1 rounded font-medium"
                    title="Dimension: {part.text}"
                >
                    {part.text}
                </span>
            {:else if part.type === "fact"}
                <span
                    class="bg-blue-200 text-blue-900 px-1 rounded font-medium"
                    title="Fact: {part.text}"
                >
                    {part.text}
                </span>
            {:else}
                    {part.text}
                {/if}
            {/each}
        </div>

        <!-- Status badges -->
        <div class="flex items-center gap-2 flex-shrink-0">
            {#if sevenWsFilledCount > 0}
                <span
                    class="px-2 py-1 rounded text-xs font-medium border {sevenWsBadgeColor()} flex items-center gap-1"
                    title="7 Ws completion status"
                >
                    {sevenWsFilledCount}/7 Ws
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
            {#if sevenWsFilledCount > 0 && onViewSevenWs}
                <button
                    onclick={() => onViewSevenWs(event)}
                    class="p-1.5 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                    title="View 7 Ws structure"
                >
                    <Icon icon="lucide:list" class="w-4 h-4" />
                </button>
            {/if}

            <button
                onclick={() => onAnnotate(event)}
                class="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title={sevenWsFilledCount > 0 ? "Edit 7 Ws structure" : "Add 7 Ws structure (Who, What, When, Where, How, How Many, Why)"}
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
                        ? "Generate dimensional entities from 7 Ws"
                        : sevenWsFilledCount > 0 && !hasHowManyEntries
                            ? "Add 'How Many' entries to generate fact table"
                            : sevenWsFilledCount > 0
                                ? "Add dimension entries (Who, What, When, Where, How, or Why) to generate entities"
                                : "Add 7 Ws structure or annotations to generate entities"
                }
            >
                <Icon icon="lucide:sparkles" class="w-4 h-4" />
            </button>

            <button
                onclick={() => onEdit(event)}
                class="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="Edit event text or type"
            >
                <Icon icon="lucide:pencil" class="w-4 h-4" />
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
