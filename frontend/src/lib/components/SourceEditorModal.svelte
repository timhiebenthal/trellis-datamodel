<script lang="ts">
    import { getSourceSystemSuggestions } from '$lib/api';

    type Props = {
        open: boolean;
        entityLabel: string;
        sources: string[];
        onConfirm: (newSources: string[]) => void;
        onCancel: () => void;
    };

    let { open, entityLabel, sources, onConfirm, onCancel }: Props = $props();

    let newSources = $state<string[]>([]);
    let sourceInput = $state('');
    let showSourceInput = $state(false);
    let suggestions = $state<string[]>([]);
    let showSuggestions = $state(false);
    let filteredSuggestions = $derived(
        suggestions.filter((s) =>
            s.toLowerCase().includes(sourceInput.toLowerCase())
        )
    );
    let activeSuggestionIndex = $state(0);

    // Load suggestions when modal opens
    $effect(() => {
        if (open) {
            loadSuggestions();
        }
    });

    async function loadSuggestions() {
        try {
            const data = await getSourceSystemSuggestions();
            suggestions = data;
        } catch (error) {
            console.error('Failed to load source system suggestions:', error);
            suggestions = [];
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            if (showSuggestions) {
                showSuggestions = false;
                event.preventDefault();
            } else {
                onCancel();
            }
        } else if (event.key === 'Enter') {
            if (showSuggestions && filteredSuggestions.length > 0) {
                // Select suggestion
                event.preventDefault();
                selectSuggestion(filteredSuggestions[activeSuggestionIndex]);
            } else if (sourceInput.trim()) {
                // Add manually entered source
                event.preventDefault();
                addSource(sourceInput.trim());
            }
        } else if (event.key === 'ArrowDown') {
            if (showSuggestions) {
                event.preventDefault();
                activeSuggestionIndex = Math.min(
                    activeSuggestionIndex + 1,
                    filteredSuggestions.length - 1
                );
            }
        } else if (event.key === 'ArrowUp') {
            if (showSuggestions) {
                event.preventDefault();
                activeSuggestionIndex = Math.max(activeSuggestionIndex - 1, 0);
            }
        } else if (event.key === 'Tab') {
            if (showSuggestions && filteredSuggestions.length > 0) {
                event.preventDefault();
                selectSuggestion(filteredSuggestions[activeSuggestionIndex]);
            }
        }
    }

    function handleInputFocus() {
        showSourceInput = true;
        showSuggestions = true;
        activeSuggestionIndex = 0;
    }

    function handleInputBlur() {
        // Delay hiding suggestions to allow click events
        setTimeout(() => {
            showSuggestions = false;
            showSourceInput = false;
        }, 200);
    }

    function handleInput() {
        showSuggestions = true;
        activeSuggestionIndex = 0;
    }

    function addSource(source: string) {
        const trimmed = source.trim();
        if (!trimmed) return;
        if (newSources.includes(trimmed)) return;

        newSources = [...newSources, trimmed];
        sourceInput = '';
        activeSuggestionIndex = 0;
    }

    function removeSource(source: string) {
        newSources = newSources.filter((s) => s !== source);
    }

    function selectSuggestion(suggestion: string) {
        addSource(suggestion);
        showSuggestions = false;
        sourceInput = '';
        activeSuggestionIndex = 0;

        // Focus input again
        setTimeout(() => {
            const input = document.querySelector(
                '.source-input'
            ) as HTMLInputElement;
            if (input) input.focus();
        }, 0);
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onCancel();
        }
    }

    function handleConfirm() {
        // Sort sources for consistency
        const sortedSources = [...newSources].sort();
        onConfirm(sortedSources);
    }

    function handleCancel() {
        onCancel();
    }

    // Initialize newSources when modal opens
    $effect(() => {
        if (open) {
            newSources = [...sources];
            sourceInput = '';
            showSourceInput = false;
            showSuggestions = false;
            activeSuggestionIndex = 0;
        }
    });
</script>

{#if open}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="source-editor-modal-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-lg w-full mx-4"
            role="document"
            tabindex="-1"
        >
            <h2
                id="source-editor-modal-title"
                class="text-lg font-semibold text-gray-900 mb-2"
            >
                Edit Source Systems
            </h2>
            <p class="text-sm text-gray-600 mb-4">
                Manage source systems for <span class="font-medium">'{entityLabel}'</span
                >. Source systems indicate the origin of data for this entity.
            </p>

            <!-- Sources Display -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Source Systems
                </label>
                <div class="flex flex-wrap gap-2 min-h-[40px] p-3 border border-gray-300 rounded-md bg-gray-50">
                    {#each newSources as source}
                        <div class="flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded border border-gray-200">
                            <span>{source}</span>
                            <button
                                onmousedown={(e) => e.preventDefault()}
                                onclick={() => removeSource(source)}
                                class="ml-1 text-gray-500 hover:text-gray-700 focus:outline-none"
                                title="Remove {source}"
                                aria-label="Remove {source}"
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="w-3 h-3"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M6 18L18 6M6 6l12 12"
                                    />
                                </svg>
                            </button>
                        </div>
                    {/each}

                    <!-- Add Source Input -->
                    <input
                        type="text"
                        class="source-input inline-input px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400 min-w-[120px] flex-1"
                        bind:value={sourceInput}
                        onfocus={handleInputFocus}
                        onblur={handleInputBlur}
                        oninput={handleInput}
                        placeholder="Type or select source system"
                        aria-label="Add source system"
                    />
                </div>

                <!-- Suggestions Dropdown -->
                {#if showSuggestions && filteredSuggestions.length > 0}
                    <div class="mt-2 border border-gray-300 rounded-md bg-white max-h-48 overflow-y-auto">
                        {#each filteredSuggestions as suggestion, index}
                            <button
                                class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 focus:bg-blue-50 focus:outline-none {index === activeSuggestionIndex ? 'bg-blue-50' : ''}"
                                onmousedown={(e) => e.preventDefault()}
                                onclick={() => selectSuggestion(suggestion)}
                                aria-label="Add {suggestion}"
                            >
                                {suggestion}
                                {#if newSources.includes(suggestion)}
                                    <span class="ml-2 text-xs text-gray-400">(added)</span>
                                {/if}
                            </button>
                        {/each}
                    </div>
                {/if}

                <p class="mt-2 text-xs text-gray-500">
                    Press Enter or comma to add. Select from suggestions for known systems.
                </p>
            </div>

            <!-- Buttons -->
            <div class="flex justify-end gap-3">
                <button
                    onclick={handleCancel}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                    Cancel
                </button>
                <button
                    onclick={handleConfirm}
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                    Save Sources
                </button>
            </div>
        </div>
    </div>
{/if}
