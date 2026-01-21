<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { BusinessEvent, Annotation } from "$lib/types";
    import { addAnnotation, removeAnnotation } from "$lib/api";

    type Props = {
        event: BusinessEvent;
        onSave: (updatedEvent: BusinessEvent) => void;
        onCancel: () => void;
    };

    let { event, onSave, onCancel }: Props = $props();

    let currentEvent = $state<BusinessEvent>(event);
    let textContainerRef: HTMLDivElement | null = $state(null);
    let showContextMenu = $state(false);
    let contextMenuPosition = $state({ x: 0, y: 0 });
    let selectedRange: { start: number; end: number; text: string } | null = $state(null);
    let showRemoveMenu = $state(false);
    let removeMenuPosition = $state({ x: 0, y: 0 });
    let annotationToRemove: { index: number; annotation: Annotation } | null = $state(null);
    let isSaving = $state(false);

    // Update currentEvent when prop changes
    $effect(() => {
        currentEvent = event;
    });

    // Render annotated text as parts
    function renderAnnotatedText(): Array<{ text: string; type?: "dimension" | "fact"; annotationIndex?: number }> {
        if (currentEvent.annotations.length === 0) {
            return [{ text: currentEvent.text }];
        }

        // Sort annotations by start position
        const sortedAnnotations = [...currentEvent.annotations].sort((a, b) => a.start_pos - b.start_pos);
        const parts: Array<{ text: string; type?: "dimension" | "fact"; annotationIndex?: number }> = [];
        let lastPos = 0;

        for (let i = 0; i < sortedAnnotations.length; i++) {
            const ann = sortedAnnotations[i];
            // Find original index in unsorted annotations
            const originalIndex = currentEvent.annotations.findIndex(
                (a) => a.start_pos === ann.start_pos && a.end_pos === ann.end_pos && a.text === ann.text
            );

            // Add text before annotation
            if (ann.start_pos > lastPos) {
                parts.push({ text: currentEvent.text.slice(lastPos, ann.start_pos) });
            }
            // Add annotated text
            parts.push({
                text: currentEvent.text.slice(ann.start_pos, ann.end_pos),
                type: ann.type,
                annotationIndex: originalIndex,
            });
            lastPos = ann.end_pos;
        }

        // Add remaining text after last annotation
        if (lastPos < currentEvent.text.length) {
            parts.push({ text: currentEvent.text.slice(lastPos) });
        }

        return parts;
    }

    // Calculate text position from DOM selection
    function calculateTextPosition(selection: Selection): { start: number; end: number; text: string } | null {
        if (!textContainerRef || selection.rangeCount === 0) {
            return null;
        }

        const range = selection.getRangeAt(0);
        const textContainer = textContainerRef;

        // Create a range from start of container to selection start
        const preRange = document.createRange();
        preRange.setStart(textContainer, 0);
        preRange.setEnd(range.startContainer, range.startOffset);

        // Get all text content before selection
        const textBefore = preRange.toString();
        const startPos = textBefore.length;

        // Get selected text
        const selectedText = range.toString();
        const trimmedText = selectedText.trim();
        
        // Calculate how many leading/trailing spaces to skip
        const leadingSpaces = selectedText.length - selectedText.trimStart().length;
        const trailingSpaces = selectedText.length - selectedText.trimEnd().length;
        
        // Adjust positions to exclude whitespace
        const adjustedStart = startPos + leadingSpaces;
        const adjustedEnd = startPos + selectedText.length - trailingSpaces;

        return {
            start: adjustedStart,
            end: adjustedEnd,
            text: trimmedText,
        };
    }

    // Check if selection overlaps with existing annotations
    function checkOverlap(start: number, end: number): boolean {
        return currentEvent.annotations.some((ann) => {
            // Check if ranges overlap
            return !(end <= ann.start_pos || start >= ann.end_pos);
        });
    }

    // Handle text selection
    function handleMouseUp(event: MouseEvent) {
        // Close any open menus first
        showContextMenu = false;
        showRemoveMenu = false;

        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0) {
            return;
        }

        const selectedText = selection.toString().trim();
        if (!selectedText) {
            return;
        }

        // Calculate position in original text
        const position = calculateTextPosition(selection);
        if (!position || position.text.length === 0) {
            return;
        }

        // Check for overlap
        if (checkOverlap(position.start, position.end)) {
            // Selection overlaps with existing annotation - show warning
            selection.removeAllRanges();
            // Show warning message
            const warningMessage = "Selection overlaps existing annotation";
            alert(warningMessage);
            return;
        }

        // Store selection info
        selectedRange = position;

        // Show context menu at cursor position
        const rect = selection.getRangeAt(0).getBoundingClientRect();
        contextMenuPosition = {
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
        };
        showContextMenu = true;

        // Close menu when clicking outside
        const closeMenu = (e: MouseEvent) => {
            if (!(e.target as HTMLElement)?.closest('.context-menu')) {
                showContextMenu = false;
                selection.removeAllRanges();
                document.removeEventListener('click', closeMenu);
            }
        };
        setTimeout(() => {
            document.addEventListener('click', closeMenu, { once: true });
        }, 0);
    }

    // Handle annotation tag selection
    async function handleTagAs(type: "dimension" | "fact") {
        if (!selectedRange) return;

        try {
            isSaving = true;
            const updatedEvent = await addAnnotation(
                currentEvent.id,
                selectedRange.text,
                type,
                selectedRange.start,
                selectedRange.end
            );
            currentEvent = updatedEvent;
            selectedRange = null;
            showContextMenu = false;
            
            // Clear selection
            window.getSelection()?.removeAllRanges();
        } catch (error) {
            console.error("Error adding annotation:", error);
            alert(`Failed to add annotation: ${error instanceof Error ? error.message : String(error)}`);
        } finally {
            isSaving = false;
        }
    }

    // Handle annotation span click
    function handleAnnotationClick(event: MouseEvent, annotationIndex: number) {
        event.stopPropagation();
        const annotation = currentEvent.annotations[annotationIndex];
        if (!annotation) return;

        annotationToRemove = { index: annotationIndex, annotation };
        
        // Position menu near the clicked span
        const target = event.target as HTMLElement;
        const rect = target.getBoundingClientRect();
        removeMenuPosition = {
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
        };
        showRemoveMenu = true;

        // Close menu when clicking outside
        const closeMenu = (e: MouseEvent) => {
            if (!(e.target as HTMLElement)?.closest('.remove-menu')) {
                showRemoveMenu = false;
                document.removeEventListener('click', closeMenu);
            }
        };
        setTimeout(() => {
            document.addEventListener('click', closeMenu, { once: true });
        }, 0);
    }

    // Handle annotation removal
    async function handleRemoveAnnotation() {
        if (!annotationToRemove) return;

        try {
            isSaving = true;
            const updatedEvent = await removeAnnotation(
                currentEvent.id,
                annotationToRemove.index
            );
            currentEvent = updatedEvent;
            annotationToRemove = null;
            showRemoveMenu = false;
        } catch (error) {
            console.error("Error removing annotation:", error);
            alert(`Failed to remove annotation: ${error instanceof Error ? error.message : String(error)}`);
        } finally {
            isSaving = false;
        }
    }

    // Handle save
    function handleSave() {
        onSave(currentEvent);
    }

    // Handle cancel
    function handleCancel() {
        onCancel();
    }

    // Close context menu on Escape
    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            if (showContextMenu) {
                showContextMenu = false;
                selectedRange = null;
                window.getSelection()?.removeAllRanges();
            }
            if (showRemoveMenu) {
                showRemoveMenu = false;
                annotationToRemove = null;
            }
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="event-annotator space-y-4">
    <div class="mb-4">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Annotate Event Text</h3>
        <p class="text-sm text-gray-600">
            Select text to tag as dimension or fact. Click on highlighted annotations to remove them.
        </p>
    </div>

    <!-- Event text container -->
    <div
        bind:this={textContainerRef}
        class="border border-gray-300 rounded-lg p-4 bg-gray-50 min-h-[120px] text-base leading-relaxed select-text"
        contenteditable="false"
        onmouseup={handleMouseUp}
        role="textbox"
        aria-label="Event text for annotation"
    >
        {#each renderAnnotatedText() as part}
            {#if part.type === "dimension"}
                <span
                    class="bg-blue-200 text-blue-900 px-1 rounded font-medium cursor-pointer hover:bg-blue-300 transition-colors"
                    title="Dimension: {part.text} (click to remove)"
                    onclick={(e) => handleAnnotationClick(e, part.annotationIndex!)}
                    data-annotation-index={part.annotationIndex}
                >
                    {part.text}
                </span>
            {:else if part.type === "fact"}
                <span
                    class="bg-green-200 text-green-900 px-1 rounded font-medium cursor-pointer hover:bg-green-300 transition-colors"
                    title="Fact: {part.text} (click to remove)"
                    onclick={(e) => handleAnnotationClick(e, part.annotationIndex!)}
                    data-annotation-index={part.annotationIndex}
                >
                    {part.text}
                </span>
            {:else}
                <span>{part.text}</span>
            {/if}
        {/each}
    </div>

    <!-- Context menu for tagging selection -->
    {#if showContextMenu && selectedRange}
        <div
            class="context-menu fixed z-50 bg-white border border-gray-300 rounded-lg shadow-lg py-1 min-w-[180px]"
            style="left: {contextMenuPosition.x}px; top: {contextMenuPosition.y}px; transform: translate(-50%, -100%);"
            role="menu"
        >
            <button
                onclick={() => handleTagAs("dimension")}
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 flex items-center gap-2"
                role="menuitem"
                disabled={isSaving}
            >
                <Icon icon="lucide:tag" class="w-4 h-4 text-blue-600" />
                Tag as Dimension
            </button>
            <button
                onclick={() => handleTagAs("fact")}
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-green-50 hover:text-green-700 flex items-center gap-2"
                role="menuitem"
                disabled={isSaving}
            >
                <Icon icon="lucide:tag" class="w-4 h-4 text-green-600" />
                Tag as Fact
            </button>
            <div class="border-t border-gray-200 my-1"></div>
            <button
                onclick={() => {
                    showContextMenu = false;
                    selectedRange = null;
                    window.getSelection()?.removeAllRanges();
                }}
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                role="menuitem"
            >
                Cancel
            </button>
        </div>
    {/if}

    <!-- Remove annotation menu -->
    {#if showRemoveMenu && annotationToRemove}
        <div
            class="remove-menu fixed z-50 bg-white border border-gray-300 rounded-lg shadow-lg py-1 min-w-[180px]"
            style="left: {removeMenuPosition.x}px; top: {removeMenuPosition.y}px; transform: translate(-50%, -100%);"
            role="menu"
        >
            <div class="px-4 py-2 text-sm text-gray-700 border-b border-gray-200">
                <div class="font-medium">Remove Annotation?</div>
                <div class="text-xs text-gray-500 mt-1">
                    "{annotationToRemove.annotation.text}" ({annotationToRemove.annotation.type})
                </div>
            </div>
            <button
                onclick={handleRemoveAnnotation}
                class="w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-50 flex items-center gap-2"
                role="menuitem"
                disabled={isSaving}
            >
                <Icon icon="lucide:trash-2" class="w-4 h-4" />
                Remove Annotation
            </button>
            <button
                onclick={() => {
                    showRemoveMenu = false;
                    annotationToRemove = null;
                }}
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                role="menuitem"
            >
                Cancel
            </button>
        </div>
    {/if}

    <!-- Action buttons -->
    <div class="flex justify-end gap-3 pt-4 border-t border-gray-200">
        <button
            onclick={handleCancel}
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            disabled={isSaving}
        >
            Cancel
        </button>
        <button
            onclick={handleSave}
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            disabled={isSaving}
        >
            {#if isSaving}
                <Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
                Saving...
            {:else}
                <Icon icon="lucide:check" class="w-4 h-4" />
                Done Annotating
            {/if}
        </button>
    </div>
</div>

<style>
    /* Prevent text selection issues */
    .event-annotator [contenteditable="false"] {
        user-select: text;
        -webkit-user-select: text;
        -moz-user-select: text;
        -ms-user-select: text;
    }
</style>
