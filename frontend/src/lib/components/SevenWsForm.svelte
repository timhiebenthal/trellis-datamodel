<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { BusinessEvent, BusinessEventSevenWs, SevenWType, SevenWsEntry, Dimension } from "$lib/types";
    import { getDimensions } from "$lib/api";
    import { onMount } from "svelte";
    import DimensionAutocomplete from "./DimensionAutocomplete.svelte";

    type Props = {
        event: BusinessEvent;
        onSave: (updatedEvent: BusinessEvent) => void;
        onCancel: () => void;
    };

    let { event, onSave, onCancel }: Props = $props();

    // W type configuration
    const W_TYPES: Array<{ type: SevenWType; label: string; icon: string; placeholder: string; tooltip: string }> = [
        { type: 'who', label: 'Who', icon: 'lucide:user', placeholder: 'e.g., customer, employee, supplier', tooltip: 'Who performed or participated in the event?' },
        { type: 'what', label: 'What', icon: 'lucide:box', placeholder: 'e.g., product, service, order', tooltip: 'What was involved in the event?' },
        { type: 'when', label: 'When', icon: 'lucide:calendar', placeholder: 'e.g., order date, delivery time', tooltip: 'When did the event occur?' },
        { type: 'where', label: 'Where', icon: 'lucide:map-pin', placeholder: 'e.g., store location, region', tooltip: 'Where did the event happen?' },
        { type: 'how', label: 'How', icon: 'lucide:settings', placeholder: 'e.g., online, in-store, phone', tooltip: 'How was the event performed?' },
        { type: 'how_many', label: 'How Many', icon: 'lucide:bar-chart-3', placeholder: 'e.g., quantity, amount, revenue', tooltip: 'What are the quantitative measures (becomes fact table)?' },
        { type: 'why', label: 'Why', icon: 'lucide:help-circle', placeholder: 'e.g., campaign, season, promotion', tooltip: 'Why did the event occur?' }
    ];

    // Form state
    let sevenWs = $state<BusinessEventSevenWs>(event.seven_ws || {
        who: [],
        what: [],
        when: [],
        where: [],
        how: [],
        how_many: [],
        why: []
    });
    let loading = $state(false);
    let error = $state<string | null>(null);

    // Error boundary state
    let hasError = $state(false);
    let errorMessage = $state<string | null>(null);

    // Dimensions for autocomplete
    let dimensions = $state<Dimension[]>([]);
    let dimensionsLoading = $state(false);

    // Delete confirmation state
    let showDeleteConfirm = $state(false);
    let entryToDelete = $state<{ wType: SevenWType; entryId: string } | null>(null);

    // Collapsed state for each W section
    let collapsedState = $state<Record<SevenWType, boolean>>({
        who: false,
        what: false,
        when: false,
        where: false,
        how: false,
        how_many: false,
        why: false
    });

    // Entry editing state
    let editingEntries = $state<Record<string, { text: string; description?: string; dimension_id?: string }>>({});

    // Calculate filled Ws count
    let filledWsCount = $derived(
        W_TYPES.filter(w => sevenWs[w.type].length > 0).length
    );

    // Validation errors
    let validationErrors = $derived.by(() => {
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

        // Check for duplicate dimension_id references
        const allDimensionIds = W_TYPES
            .filter(w => w.type !== 'how_many')
            .flatMap(w => sevenWs[w.type].map(e => e.dimension_id))
            .filter((id): id is string => id !== undefined);

        const uniqueIds = new Set(allDimensionIds);
        if (allDimensionIds.length !== uniqueIds.size) {
            const duplicates = allDimensionIds.filter(id => {
                const count = allDimensionIds.filter(d => d === id).length;
                return count > 1;
            });
            const uniqueDuplicates = Array.from(new Set(duplicates));
            errors.push(`Duplicate dimension reference(s) detected: ${uniqueDuplicates.join(', ')}. Each dimension should only be used once per event.`);
        }

        return errors;
    });

    let isValid = $derived(validationErrors.length === 0 && !hasError);

    // Initialize on mount
    $effect(() => {
        sevenWs = event.seven_ws || {
            who: [],
            what: [],
            when: [],
            where: [],
            how: [],
            how_many: [],
            why: []
        };
    });

    // Load dimensions on mount for autocomplete
    onMount(async () => {
        try {
            dimensionsLoading = true;
            dimensions = await getDimensions();
        } catch (e) {
            console.error('Failed to load dimensions:', e);
            dimensions = [];
        } finally {
            dimensionsLoading = false;
        }
    });

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) {
            onCancel();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onCancel();
        } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            handleSave();
        }
    }

    function toggleCollapse(wType: SevenWType) {
        collapsedState[wType] = !collapsedState[wType];
    }

    function addEntry(wType: SevenWType) {
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
        
        // Initialize editing state for new entry
        editingEntries[newEntry.id] = { text: "", description: "" };
        
        // Expand section when adding entry
        collapsedState[wType] = false;
    }

    function removeEntry(wType: SevenWType, entryId: string) {
        sevenWs = {
            ...sevenWs,
            [wType]: sevenWs[wType].filter(e => e.id !== entryId)
        };
        
        // Remove from editing state
        delete editingEntries[entryId];
    }

    function updateEntryText(wType: SevenWType, entryId: string, text: string) {
        editingEntries[entryId] = { ...editingEntries[entryId], text };
        
        sevenWs = {
            ...sevenWs,
            [wType]: sevenWs[wType].map(e => 
                e.id === entryId ? { ...e, text } : e
            )
        };
    }

    function updateEntryDescription(wType: SevenWType, entryId: string, description: string) {
        editingEntries[entryId] = { ...editingEntries[entryId], description };
        
        sevenWs = {
            ...sevenWs,
            [wType]: sevenWs[wType].map(e => 
                e.id === entryId ? { ...e, description } : e
            )
        };
    }

    async function handleSave() {
        error = null;
        loading = true;

        try {
            // Validate no empty text entries
            for (const w of W_TYPES) {
                for (const entry of sevenWs[w.type]) {
                    if (!entry.text.trim()) {
                        throw new Error(`All entries must have text. Please check the ${w.label} section.`);
                    }
                }
            }

            // Create updated event
            const updatedEvent: BusinessEvent = {
                ...event,
                seven_ws: sevenWs,
                updated_at: new Date().toISOString()
            };

            onSave(updatedEvent);
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Failed to save 7 Ws";
            error = errorMessage;
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

{#if true}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center backdrop-blur-sm"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="seven-ws-modal-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            role="document"
            tabindex="-1"
        >
            <!-- Header -->
            <div class="flex items-center justify-between p-6 border-b border-gray-200">
                <div class="flex items-center gap-3">
                    <div>
                        <h2 id="seven-ws-modal-title" class="text-xl font-semibold text-gray-900">
                            7 Ws - Business Event
                        </h2>
                        <p class="text-sm text-gray-500 mt-1">
                            {event.text}
                        </p>
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <!-- Progress Badge -->
                    <div
                        class="px-3 py-1 rounded-full text-sm font-medium {isValid ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}"
                    >
                        {filledWsCount}/7 Ws completed
                    </div>
                    <button
                        class="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                        onclick={handleCancel}
                        aria-label="Close"
                        disabled={loading}
                    >
                        <Icon icon="lucide:x" class="w-5 h-5" />
                    </button>
                </div>
            </div>

            <!-- Form -->
            <div class="p-6 space-y-4">
                <!-- 7 Ws Sections -->
                {#each W_TYPES as wType}
                    <div class="border border-gray-200 rounded-lg overflow-hidden">
                        <!-- Section Header -->
                        <button
                            class="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
                            onclick={() => toggleCollapse(wType.type)}
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
                                <!-- Tooltip icon -->
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
                                                    oninput={(e) => updateEntryText(wType.type, entry.id, e.currentTarget.value)}
                                                    placeholder={wType.placeholder}
                                                    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                                                    maxlength={200}
                                                    disabled={loading}
                                                />
                                                <!-- Description Input -->
                                                <input
                                                    type="text"
                                                    value={entry.description || ''}
                                                    oninput={(e) => updateEntryDescription(wType.type, entry.id, e.currentTarget.value)}
                                                    placeholder="Optional description..."
                                                    class="w-full px-3 py-2 border border-gray-200 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-xs text-gray-600"
                                                    maxlength={500}
                                                    disabled={loading}
                                                />
                                            </div>
                                            <button
                                                class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors mt-1"
                                                onclick={() => removeEntry(wType.type, entry.id)}
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
                                    onclick={() => addEntry(wType.type)}
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

                <!-- Validation Errors -->
                {#if validationErrors.length > 0}
                    <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-2">
                        <div class="flex items-center gap-2 text-amber-800 font-medium">
                            <Icon icon="lucide:alert-triangle" class="w-5 h-5" />
                            <span>Entity Generation Requirements</span>
                        </div>
                        <ul class="space-y-1 pl-7">
                            {#each validationErrors as error}
                                <li class="text-sm text-amber-700">• {error}</li>
                            {/each}
                        </ul>
                        <p class="text-xs text-amber-600 mt-2">
                            You can still save the event, but you won't be able to generate entities until these requirements are met.
                        </p>
                    </div>
                {/if}

                <!-- Error Message -->
                {#if error}
                    <div
                        class="flex items-center gap-3 text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3"
                    >
                        <Icon icon="lucide:alert-circle" class="w-5 h-5 flex-shrink-0" />
                        <span class="text-sm">{error}</span>
                    </div>
                {/if}

                <!-- Actions -->
                <div class="flex justify-between items-center pt-4 border-t border-gray-200">
                    <p class="text-xs text-gray-500">
                        Press Ctrl+Enter to save
                    </p>
                    <div class="flex gap-3">
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
                            disabled={loading}
                        >
                            {#if loading}
                                <Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
                                <span>Saving...</span>
                            {:else}
                                <Icon icon="lucide:save" class="w-4 h-4" />
                                <span>Save 7 Ws</span>
                            {/if}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
{/if}
