<script lang="ts">
    import Icon from "@iconify/svelte";
    import { createBusinessEvent, updateBusinessEvent, getBusinessEventDomains } from "$lib/api";
    import type { BusinessEvent, BusinessEventType, BusinessEventSevenWs, SevenWType, SevenWsEntry } from "$lib/types";
    import { onMount } from "svelte";

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
    let eventDomain = $state<string | null>(null);
    let sevenWs = $state<BusinessEventSevenWs>({
        who: [],
        what: [],
        when: [],
        where: [],
        how: [],
        how_many: [],
        why: []
    });
    let showSevenWs = $state(false);
    let loading = $state(false);
    let error = $state<string | null>(null);
    let domains = $state<string[]>([]);

    // Annotations configuration (7 Ws: Who, What, When, Where, How, How Many, Why)
    const W_TYPES: Array<{ type: SevenWType; label: string; icon: string; placeholder: string; tooltip: string }> = [
        { type: 'who', label: 'Who', icon: 'lucide:user', placeholder: 'e.g., customer, employee, supplier', tooltip: 'Who performed or participated in event?' },
        { type: 'what', label: 'What', icon: 'lucide:box', placeholder: 'e.g., product, service, order', tooltip: 'What was involved in the event?' },
        { type: 'when', label: 'When', icon: 'lucide:calendar', placeholder: 'e.g., order date, delivery time', tooltip: 'When did the event occur?' },
        { type: 'where', label: 'Where', icon: 'lucide:map-pin', placeholder: 'e.g., store location, region', tooltip: 'Where did the event happen?' },
        { type: 'how', label: 'How', icon: 'lucide:settings', placeholder: 'e.g., online, in-store, phone', tooltip: 'How was the event performed?' },
        { type: 'how_many', label: 'How Many', icon: 'lucide:bar-chart-3', placeholder: 'e.g., quantity, amount, revenue', tooltip: 'What are the quantitative measures (becomes fact table)?' },
        { type: 'why', label: 'Why', icon: 'lucide:help-circle', placeholder: 'e.g., campaign, season, promotion', tooltip: 'Why did the event occur?' }
    ];

    // Annotations collapsed state
    let collapsedState = $state<Record<SevenWType, boolean>>({
        who: false,
        what: false,
        when: false,
        where: false,
        how: false,
        how_many: false,
        why: false
    });

    // Annotations editing state
    let editingEntries = $state<Record<string, { text: string; description?: string }>>({});

    // Calculate filled annotations count
    let filledWsCount = $derived(
        W_TYPES.filter(w => sevenWs[w.type].length > 0).length
    );

    // Helper function to convert domain to title case
    function toTitleCase(str: string): string {
        return str.trim().charAt(0).toUpperCase() + str.trim().slice(1).toLowerCase();
    }

    // Character limit
    const MAX_TEXT_LENGTH = 500;
    let characterCount = $derived(eventText.length);
    let remainingChars = $derived(MAX_TEXT_LENGTH - characterCount);

    // Annotations validation errors
    let sevenWsValidationErrors = $derived.by(() => {
        const errors: string[] = [];

        // Count dimension entries (all except how_many)
        const dimensionEntries = W_TYPES
            .filter(w => w.type !== 'how_many')
            .reduce((sum, w) => sum + sevenWs[w.type].length, 0);

        // Count how_many entries
        const howManyEntries = sevenWs.how_many.length;

        if (dimensionEntries === 0) {
            errors.push("At least one dimension entry (Who, What, When, Where, How, or Why) is required for entity generation");
        }

        if (howManyEntries === 0) {
            errors.push("At least one 'How Many' entry is required for entity generation (becomes fact table)");
        }

        return errors;
    });

    let isValid = $derived.by(() => {
        if (eventText.trim().length === 0) return false;
        if (eventText.length > MAX_TEXT_LENGTH) return false;
        if (!eventType) return false;
        if (loading) return false;

        // If annotations are shown and have entries, validate them
        if (showSevenWs && filledWsCount > 0) {
            for (const w of W_TYPES) {
                for (const entry of sevenWs[w.type]) {
                    if (!entry.text.trim()) return false;
                }
            }
        }

        return true;
    });

    // Load domains when modal opens
    $effect(() => {
        if (open) {
            async function loadDomains() {
                try {
                    domains = await getBusinessEventDomains();
                } catch (e) {
                    console.warn('Failed to load domains:', e);
                    domains = [];
                }
            }
            
            loadDomains();
            
            // Initialize form
            if (event) {
                // Edit mode: populate form with existing event data
                eventText = event.text;
                eventType = event.type;
                eventDomain = event.domain || null;
                sevenWs = event.annotations || {
                    who: [],
                    what: [],
                    when: [],
                    where: [],
                    how: [],
                    how_many: [],
                    why: []
                };
                showSevenWs = !!event.annotations && (event.annotations.who.length > 0 || event.annotations.what.length > 0 || event.annotations.how_many.length > 0);
            } else {
                // Create mode: reset form
                eventText = "";
                eventType = "discrete";
                eventDomain = null;
                sevenWs = {
                    who: [],
                    what: [],
                    when: [],
                    where: [],
                    how: [],
                    how_many: [],
                    why: []
                };
                showSevenWs = false;
            }
            error = null;
            loading = false;
        }
    });


    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onCancel();
        } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            handleSave();
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onCancel();
        }
    }

    // Annotations helper functions
    function toggleSevenWsCollapse(wType: SevenWType) {
        collapsedState[wType] = !collapsedState[wType];
    }

    function addSevenWsEntry(wType: SevenWType) {
        const newEntry: SevenWsEntry = {
            id: `new_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            text: "",
            description: "",
            dimension_id: undefined
        };

        sevenWs = {
            ...sevenWs,
            [wType]: [...sevenWs[wType], newEntry]
        };

        editingEntries[newEntry.id] = { text: "", description: "" };
        collapsedState[wType] = false;
    }

    function removeSevenWsEntry(wType: SevenWType, entryId: string) {
        sevenWs = {
            ...sevenWs,
            [wType]: sevenWs[wType].filter(e => e.id !== entryId)
        };

        delete editingEntries[entryId];
    }

    function updateSevenWsEntryText(wType: SevenWType, entryId: string, text: string) {
        editingEntries[entryId] = { ...editingEntries[entryId], text };

        sevenWs = {
            ...sevenWs,
            [wType]: sevenWs[wType].map(e =>
                e.id === entryId ? { ...e, text } : e
            )
        };
    }

    function updateSevenWsEntryDescription(wType: SevenWType, entryId: string, description: string) {
        editingEntries[entryId] = { ...editingEntries[entryId], description };

        sevenWs = {
            ...sevenWs,
            [wType]: sevenWs[wType].map(e =>
                e.id === entryId ? { ...e, description } : e
            )
        };
    }


    async function handleSave() {
        // Validate text length before API call
        if (eventText.length > MAX_TEXT_LENGTH) {
            error = `Event text cannot exceed ${MAX_TEXT_LENGTH} characters`;
            return;
        }

        if (!isValid) return;

        // Validate annotations entries if shown and have data
        if (showSevenWs && filledWsCount > 0) {
            for (const w of W_TYPES) {
                for (const entry of sevenWs[w.type]) {
                    if (!entry.text.trim()) {
                        error = `All annotation entries must have text. Please check ${w.label} section.`;
                        return;
                    }
                }
            }

            // Validate annotations requirements for entity generation
            if (sevenWsValidationErrors.length > 0) {
                error = sevenWsValidationErrors[0];
                return;
            }
        }

        error = null;
        loading = true;

        try {
            if (event) {
                // Update existing event
                const updates: Partial<BusinessEvent> = {
                    text: eventText.trim(),
                    type: eventType,
                    domain: eventDomain
                };

                // Include annotations in request if annotations are shown and have data
                if (showSevenWs && filledWsCount > 0) {
                    updates.annotations = sevenWs;
                }

                await updateBusinessEvent(event.id, updates);
            } else {
                // Create new event
                await createBusinessEvent(
                    eventText.trim(),
                    eventType,
                    eventDomain
                );
                // Note: Annotations can be added in a separate edit flow after creation
                // This allows users to create basic events first, then add annotations later
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
            } else if (errorMessage.includes("annotation_type")) {
                error = "Invalid annotation data. Please check your entries and try again.";
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
                        {#if eventText.trim().length === 0}
                            <span class="text-xs text-red-600">Event text is required</span>
                        {:else if eventText.length > MAX_TEXT_LENGTH}
                            <span class="text-xs text-red-600">Event text cannot exceed {MAX_TEXT_LENGTH} characters</span>
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
                </div>

                <!-- Business Domain -->
                <div>
                    <div class="flex items-center gap-2 mb-2">
                        <label for="event-domain" class="block text-sm font-medium text-gray-700">
                            Business Domain
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
                                        Optional business domain classification (e.g., Sales, Marketing, Finance).
                                        Helps organize and filter events.
                                    </div>
                                </div>
                                <div class="absolute left-4 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                            </div>
                        </div>
                    </div>
                    <select
                        id="event-domain"
                        bind:value={eventDomain}
                        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        disabled={loading}
                    >
                        <option value={null}>No Domain</option>
                        {#each domains as domain}
                            <option value={domain}>{toTitleCase(domain)}</option>
                        {/each}
                    </select>
                </div>

                <!-- 7 Ws Toggle -->
                <div class="flex items-center justify-between pt-4 border-t border-gray-200">
                    <div class="flex items-center gap-2">
                        <button
                            type="button"
                            onclick={() => showSevenWs = !showSevenWs}
                            class="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center gap-2"
                            disabled={loading}
                        >
                            <Icon icon={showSevenWs ? "lucide:chevron-up" : "lucide:chevron-down"} class="w-4 h-4" />
                            <span>{showSevenWs ? "Hide 7 Ws" : "Add 7 Ws (optional)"}</span>
                        </button>
                        {#if filledWsCount > 0}
                            <span class="text-xs text-gray-500">({filledWsCount}/7 filled)</span>
                        {/if}
                    </div>
                </div>

                <!-- 7 Ws Form -->
                {#if showSevenWs}
                    <div class="pt-4">
                        <!-- 7 Ws Sections -->
                        {#each W_TYPES as wType}
                            <div class="border border-gray-200 rounded-lg overflow-hidden mb-3">
                                <!-- Section Header -->
                                <button
                                    class="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
                                    onclick={() => toggleSevenWsCollapse(wType.type)}
                                    aria-expanded={!collapsedState[wType.type]}
                                    aria-controls={`section-${wType.type}`}
                                >
                                    <div class="flex items-center gap-3">
                                        <div
                                            class="p-2 rounded-md {wType.type === 'how_many' ? 'bg-blue-100 text-blue-900' : 'bg-green-100 text-green-900'}"
                                        >
                                            <Icon icon={wType.icon} class="w-5 h-5" />
                                        </div>
                                        <div class="text-left">
                                            <div class="flex items-center gap-2">
                                                <span class="font-medium text-gray-900">{wType.label}</span>
                                                {#if sevenWs[wType.type].length > 0}
                                                    <span class="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full">
                                                        {sevenWs[wType.type].length}
                                                    </span>
                                                {/if}
                                            </div>
                                            <p class="text-xs text-gray-500">{wType.tooltip}</p>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <div class="group relative">
                                            <Icon
                                                icon="lucide:info"
                                                class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                                            />
                                            <div class="absolute right-0 bottom-full mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity z-10">
                                                {wType.tooltip}
                                                <div class="absolute right-4 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                                            </div>
                                        </div>
                                        <Icon
                                            icon={collapsedState[wType.type] ? 'lucide:chevron-down' : 'lucide:chevron-up'}
                                            class="w-5 h-5 text-gray-500 transition-transform"
                                        />
                                    </div>
                                </button>

                                <!-- Section Content -->
                                {#if !collapsedState[wType.type]}
                                    <div id={`section-${wType.type}`} class="p-4 space-y-3">
                                        <!-- Entries List -->
                                        {#if sevenWs[wType.type].length > 0}
                                            {#each sevenWs[wType.type] as entry}
                                                <div class="flex items-start gap-2 p-3 bg-gray-50 rounded-md">
                                                    <div class="flex-1 space-y-2">
                                                        <!-- Text Input -->
                                                        <input
                                                            type="text"
                                                            value={entry.text}
                                                            oninput={(e) => updateSevenWsEntryText(wType.type, entry.id, e.currentTarget.value)}
                                                            placeholder={wType.placeholder}
                                                            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                                                            maxlength={200}
                                                            disabled={loading}
                                                        />
                                                        <!-- Description Input -->
                                                        <input
                                                            type="text"
                                                            value={entry.description || ''}
                                                            oninput={(e) => updateSevenWsEntryDescription(wType.type, entry.id, e.currentTarget.value)}
                                                            placeholder="Optional description..."
                                                            class="w-full px-3 py-2 border border-gray-200 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-xs text-gray-600"
                                                            maxlength={500}
                                                            disabled={loading}
                                                        />
                                                    </div>
                                                    <button
                                                        class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors mt-1"
                                                        onclick={() => removeSevenWsEntry(wType.type, entry.id)}
                                                        aria-label="Remove entry"
                                                        disabled={loading}
                                                        title="Remove entry"
                                                    >
                                                        <Icon icon="lucide:trash-2" class="w-4 h-4" />
                                                    </button>
                                                </div>
                                            {/each}
                                        {:else}
                                            <div class="text-center py-6 text-gray-400 text-sm">
                                                No entries yet. Click "Add Entry" to add one.
                                            </div>
                                        {/if}

                                        <!-- Add Entry Button -->
                                        <button
                                            type="button"
                                            onclick={() => addSevenWsEntry(wType.type)}
                                            class="w-full py-2 px-4 border-2 border-dashed border-gray-300 rounded-md text-sm font-medium text-gray-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors flex items-center justify-center gap-2"
                                            disabled={loading}
                                        >
                                            <Icon icon="lucide:plus" class="w-4 h-4" />
                                            <span>Add Entry</span>
                                        </button>
                                    </div>
                                {/if}
                            </div>
                        {/each}

                        <!-- Annotations Validation Errors -->
                        {#if sevenWsValidationErrors.length > 0}
                            <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-2">
                                <div class="flex items-center gap-2 text-amber-800 font-medium">
                                    <Icon icon="lucide:alert-triangle" class="w-5 h-5" />
                                    <span>Entity Generation Requirements</span>
                                </div>
                                <ul class="space-y-1 pl-7">
                                    {#each sevenWsValidationErrors as error}
                                        <li class="text-sm text-amber-700">• {error}</li>
                                    {/each}
                                </ul>
                                <p class="text-xs text-amber-600 mt-2">
                                    You can still save the event, but you won't be able to generate entities until these requirements are met.
                                </p>
                            </div>
                        {/if}
                    </div>
                {/if}

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
