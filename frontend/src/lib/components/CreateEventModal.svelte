<script lang="ts">
    import Icon from "@iconify/svelte";
    import { createBusinessEvent, updateBusinessEvent } from "$lib/api";
    import type { BusinessEvent, BusinessEventType } from "$lib/types";

    type Props = {
        open: boolean;
        event?: BusinessEvent;
        onSave: () => void;
        onCancel: () => void;
    };

    let { open, event, onSave, onCancel }: Props = $props();

    // Form state
    let eventText = $state("");
    let eventType = $state<BusinessEventType>("discrete");
    let loading = $state(false);
    let error = $state<string | null>(null);

    // Character limit
    const MAX_TEXT_LENGTH = 500;
    let characterCount = $derived(eventText.length);
    let remainingChars = $derived(MAX_TEXT_LENGTH - characterCount);

    // Validation
    let textError = $derived.by(() => {
        if (eventText.trim().length === 0) {
            return "Event text is required";
        }
        if (eventText.length > MAX_TEXT_LENGTH) {
            return `Event text cannot exceed ${MAX_TEXT_LENGTH} characters`;
        }
        return null;
    });
    let typeError = $derived(eventType ? null : "Event type is required");
    let isValid = $derived(textError === null && !typeError && !loading);

    // Initialize form when modal opens or event changes
    $effect(() => {
        if (open) {
            if (event) {
                // Edit mode: populate form with existing event data
                eventText = event.text;
                eventType = event.type;
            } else {
                // Create mode: reset form
                eventText = "";
                eventType = "discrete";
            }
            error = null;
            loading = false;
        }
    });

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

    async function handleSave() {
        // Validate text length before API call
        if (eventText.length > MAX_TEXT_LENGTH) {
            error = `Event text cannot exceed ${MAX_TEXT_LENGTH} characters`;
            return;
        }

        if (!isValid) return;

        error = null;
        loading = true;

        try {
            if (event) {
                // Update existing event
                await updateBusinessEvent(event.id, {
                    text: eventText.trim(),
                    type: eventType,
                });
            } else {
                // Create new event
                await createBusinessEvent(eventText.trim(), eventType);
            }
            // Success: close modal and refresh list
            onSave();
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Failed to save event";
            // Provide user-friendly error messages
            if (errorMessage.includes("400") || errorMessage.includes("validation")) {
                error = "Invalid event data. Please check your input and try again.";
            } else if (errorMessage.includes("500") || errorMessage.includes("server")) {
                error = "Server error. Please try again later.";
            } else {
                error = errorMessage;
            }
        } finally {
            loading = false;
        }
    }

    function handleCancel() {
        error = null;
        loading = false;
        onCancel();
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
        aria-labelledby="event-modal-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            role="document"
            tabindex="-1"
        >
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <h2 id="event-modal-title" class="text-xl font-semibold text-gray-900">
                    {event ? "Edit Event" : "Create Event"}
                </h2>
                <button
                    class="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                    onclick={handleCancel}
                    aria-label="Close"
                    disabled={loading}
                >
                    <Icon icon="lucide:x" class="w-5 h-5" />
                </button>
            </div>

            <!-- Form -->
            <div class="space-y-4">
                <!-- Event Text -->
                <div>
                    <label for="event-text" class="block text-sm font-medium text-gray-700 mb-2">
                        Event Description
                    </label>
                    <textarea
                        id="event-text"
                        bind:value={eventText}
                        maxlength={MAX_TEXT_LENGTH}
                        rows="4"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        placeholder="e.g., customer buys product"
                        disabled={loading}
                    ></textarea>
                    <div class="flex items-center justify-between mt-1">
                        <span class="text-xs text-gray-500">
                            {remainingChars} characters remaining
                        </span>
                        {#if textError}
                            <span class="text-xs text-red-600">{textError}</span>
                        {/if}
                    </div>
                </div>

                <!-- Event Type -->
                <div>
                    <div class="flex items-center gap-2 mb-2">
                        <label for="event-type" class="block text-sm font-medium text-gray-700">
                            Event Type
                        </label>
                        <div class="group relative">
                            <Icon
                                icon="lucide:help-circle"
                                class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                            />
                            <!-- Tooltip -->
                            <div
                                class="absolute left-0 bottom-full mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity z-10"
                            >
                                <div class="space-y-2">
                                    <div>
                                        <strong class="text-blue-300">Discrete:</strong> One-time
                                        events (e.g., "customer buys product")
                                    </div>
                                    <div>
                                        <strong class="text-yellow-300">Evolving:</strong> Events
                                        that change over time (e.g., "sales opportunity funnel")
                                    </div>
                                    <div>
                                        <strong class="text-purple-300">Recurring:</strong> Events
                                        that repeat (e.g., "monthly account statement")
                                    </div>
                                </div>
                                <div class="absolute left-4 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                            </div>
                        </div>
                    </div>
                    <select
                        id="event-type"
                        bind:value={eventType}
                        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        disabled={loading}
                    >
                        <option value="discrete">Discrete</option>
                        <option value="evolving">Evolving</option>
                        <option value="recurring">Recurring</option>
                    </select>
                    {#if typeError}
                        <span class="text-xs text-red-600 mt-1 block">{typeError}</span>
                    {/if}
                </div>

                <!-- Error Message -->
                {#if error}
                    <div
                        class="flex items-center gap-3 text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3"
                    >
                        <Icon icon="lucide:alert-triangle" class="w-5 h-5 flex-shrink-0" />
                        <span class="text-sm">{error}</span>
                    </div>
                {/if}

                <!-- Actions -->
                <div class="flex justify-end gap-3 pt-4 border-t border-gray-200">
                    <button
                        onclick={handleCancel}
                        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        onclick={handleSave}
                        class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        disabled={!isValid}
                    >
                        {#if loading}
                            <Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
                            <span>Saving...</span>
                        {:else}
                            <Icon icon="lucide:save" class="w-4 h-4" />
                            <span>{event ? "Update" : "Create"}</span>
                        {/if}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
