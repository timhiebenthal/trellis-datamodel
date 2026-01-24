<script lang="ts">
    import Icon from "@iconify/svelte";
    import DimensionAutocomplete from "./DimensionAutocomplete.svelte";
    import type { SevenWsEntry, Dimension, SevenWType } from "$lib/types";

    type Props = {
        w_type: SevenWType;
        entries: SevenWsEntry[];
        onAdd: (entry: SevenWsEntry) => void;
        onUpdate: (entryId: string, entry: SevenWsEntry) => void;
        onRemove: (entryId: string) => void;
        dimensions?: Dimension[];
    };

    let { w_type, entries, onAdd, onUpdate, onRemove, dimensions = [] }: Props = $props();

    let newEntryText = $state("");
    let newEntryDescription = $state("");
    let newEntryDimensionId = $state("");
    let showNewEntryForm = $state(false);

    // W-specific icons
    const wIcons: Record<SevenWType, string> = {
        who: "lucide:user",
        what: "lucide:box",
        when: "lucide:calendar",
        where: "lucide:map",
        how: "lucide:settings",
        how_many: "lucide:bar-chart-3",
        why: "lucide:help-circle",
    };

    // W-specific labels (capitalized)
    const wLabels: Record<SevenWType, string> = {
        who: "Who",
        what: "What",
        when: "When",
        where: "Where",
        how: "How",
        how_many: "How Many",
        why: "Why",
    };

    // W-specific colors (for styling)
    const wColors: Record<SevenWType, { bg: string; text: string; border: string }> = {
        who: { bg: "bg-green-100", text: "text-green-900", border: "border-green-300" },
        what: { bg: "bg-green-100", text: "text-green-900", border: "border-green-300" },
        when: { bg: "bg-green-100", text: "text-green-900", border: "border-green-300" },
        where: { bg: "bg-green-100", text: "text-green-900", border: "border-green-300" },
        how: { bg: "bg-green-100", text: "text-green-900", border: "border-green-300" },
        how_many: { bg: "bg-blue-100", text: "text-blue-900", border: "border-blue-300" },
        why: { bg: "bg-green-100", text: "text-green-900", border: "border-green-300" },
    };

    const MAX_TEXT_LENGTH = 200;
    const MAX_DESCRIPTION_LENGTH = 500;

    // Validation for new entry
    let newTextError = $derived.by(() => {
        if (newEntryText.trim().length === 0) {
            return "Text is required";
        }
        if (newEntryText.length > MAX_TEXT_LENGTH) {
            return `Text cannot exceed ${MAX_TEXT_LENGTH} characters`;
        }
        // Check for duplicates
        const isDuplicate = entries.some(
            (e) => e.text.toLowerCase() === newEntryText.toLowerCase()
        );
        if (isDuplicate) {
            return 'This entry already exists. Use the existing one or edit it.';
        }
        return null;
    });

    let canAddNew = $derived.by(() => {
        return newTextError === null;
    });

    function handleAddNew() {
        if (!canAddNew) return;

        const newEntry: SevenWsEntry = {
            id: `${w_type}_${Date.now()}`,
            text: newEntryText.trim(),
            description: newEntryDescription.trim() || undefined,
            dimension_id: newEntryDimensionId || undefined,
            attributes: {},
        };

        onAdd(newEntry);

        // Reset form
        newEntryText = "";
        newEntryDescription = "";
        newEntryDimensionId = "";
        showNewEntryForm = false;
    }

    function handleUpdateEntry(entryId: string, field: 'text' | 'description' | 'dimension_id', value: string) {
        const entry = entries.find((e) => e.id === entryId);
        if (!entry) return;

        const updated: SevenWsEntry = {
            ...entry,
            [field]: value || undefined,
        };

        onUpdate(entryId, updated);
    }

    function handleRemoveEntry(entryId: string) {
        onRemove(entryId);
    }

    function getIcon(iconName: string) {
        return wIcons[w_type as SevenWType];
    }

    function getLabel(labelKey: SevenWType) {
        return wLabels[w_type];
    }

    function getColors() {
        return wColors[w_type];
    }
</script>

<div class="border border-gray-200 rounded-lg overflow-hidden">
    <!-- Header -->
    <button
        onclick={() => showNewEntryForm = !showNewEntryForm}
        class="w-full px-4 py-3 flex items-center justify-between {w_type === 'how_many' ? 'bg-blue-50' : 'bg-green-50'} hover:opacity-90 transition-opacity"
    >
        <div class="flex items-center gap-3">
            <Icon icon={getIcon('')} class="w-5 h-5 {w_type === 'how_many' ? 'text-blue-700' : 'text-green-700'}" />
            <span class="font-semibold {w_type === 'how_many' ? 'text-blue-900' : 'text-green-900'}">
                {getLabel(w_type)}
            </span>
            <span class="text-xs px-2 py-1 bg-white border border-gray-200 rounded-full">
                {entries.length} {entries.length === 1 ? 'entry' : 'entries'}
            </span>
        </div>
        <Icon
            icon={showNewEntryForm ? "lucide:chevron-up" : "lucide:chevron-down"}
            class="w-5 h-5 text-gray-600"
        />
    </button>

    <!-- Entry List -->
    {#if showNewEntryForm || entries.length > 0}
        <div class="divide-y divide-gray-200 bg-white">
            <!-- Existing Entries -->
            {#each entries as entry}
                <div class="px-4 py-3 hover:bg-gray-50">
                    <div class="flex items-start justify-between gap-4">
                        <div class="flex-1 space-y-2">
                            <!-- Text -->
                            <div class="flex items-center gap-2">
                                <span class="font-medium text-gray-900">{entry.text}</span>
                                {#if entry.dimension_id}
                                    <span class="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                                        Dimension: {entry.dimension_id}
                                    </span>
                                {/if}
                            </div>

                            <!-- Description -->
                            {#if entry.description}
                                <p class="text-sm text-gray-600">
                                    {entry.description}
                                </p>
                            {/if}
                        </div>

                        <!-- Actions -->
                        <div class="flex items-center gap-2">
                            <button
                                type="button"
                                onclick={() => handleRemoveEntry(entry.id)}
                                class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                aria-label="Remove entry"
                                title="Remove entry"
                            >
                                <Icon icon="lucide:trash-2" class="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            {/each}

            <!-- Add New Entry Form -->
            {#if showNewEntryForm}
                <div class="px-4 py-3 bg-gray-50">
                    <div class="space-y-3">
                        <!-- Text Input -->
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">
                                Entry Text <span class="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                bind:value={newEntryText}
                                maxlength={MAX_TEXT_LENGTH}
                                placeholder="e.g., customer, product, date"
                                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                            />
                            <div class="flex items-center justify-between mt-1">
                                <span class="text-xs text-gray-500">
                                    {MAX_TEXT_LENGTH - newEntryText.length} characters remaining
                                </span>
                                {#if newTextError}
                                    <span class="text-xs text-red-600">{newTextError}</span>
                                {/if}
                            </div>
                        </div>

                        <!-- Dimension Autocomplete -->
                        {#if dimensions && dimensions.length > 0}
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                    Link to Existing Dimension <span class="text-gray-400 font-normal">(optional)</span>
                                </label>
                                <DimensionAutocomplete
                                    textValue={newEntryDimensionId}
                                    onTextChange={(val) => newEntryDimensionId = val}
                                    onSelectDimension={(dimension) => {
                                        newEntryDimensionId = dimension.id;
                                        if (!newEntryText) {
                                            newEntryText = dimension.label;
                                        }
                                    }}
                                    {dimensions}
                                    filterBy={w_type === 'how_many' ? undefined : w_type}
                                    allowedIds={null}
                                    placeholder="Select existing dimension or leave blank to create new"
                                />
                            </div>
                        {/if}

                        <!-- Description (Optional) -->
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">
                                Description <span class="text-gray-400 font-normal">(optional)</span>
                            </label>
                            <textarea
                                bind:value={newEntryDescription}
                                maxlength={MAX_DESCRIPTION_LENGTH}
                                rows="2"
                                placeholder="Add more details about this entry..."
                                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm resize-none"
                            />
                            <div class="mt-1">
                                <span class="text-xs text-gray-500">
                                    {MAX_DESCRIPTION_LENGTH - newEntryDescription.length} characters remaining
                                </span>
                            </div>
                        </div>

                        <!-- Add Button -->
                        <div class="flex items-center justify-between pt-2">
                            <button
                                type="button"
                                onclick={() => showNewEntryForm = false}
                                class="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onclick={handleAddNew}
                                disabled={!canAddNew}
                                class="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Add Entry
                            </button>
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    {/if}
</div>
