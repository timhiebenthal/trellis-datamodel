<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { Dimension, SevenWType } from "$lib/types";

    type Props = {
        value: string;
        onChange: (value: string) => void;
        dimensions: Dimension[];
        filterBy?: SevenWType;
        onCreateNew?: (text: string) => void;
        disabled?: boolean;
        placeholder?: string;
        loading?: boolean;
    };

    let { value, onChange, dimensions, filterBy, onCreateNew, disabled = false, placeholder = "Select or create dimension...", loading = false }: Props = $props();

    let showDropdown = $state(false);
    let searchInput = $state("");
    let activeIndex = $state(0);
    let containerRef = $state<HTMLDivElement>();
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    // Computed filtered dimensions
    let filteredDimensions = $derived.by(() => {
        return dimensions.filter((d) => {
            // Filter by annotation_type if specified
            if (filterBy && d.annotation_type !== filterBy) {
                return false;
            }
            // Filter by search text
            const searchLower = searchInput.toLowerCase();
            return (
                d.label.toLowerCase().includes(searchLower) ||
                d.id.toLowerCase().includes(searchLower)
            );
        });
    });

    // Check if text already exists
    let existingDimension = $derived.by(() => {
        return filteredDimensions.find((d) =>
            d.label.toLowerCase() === searchInput.toLowerCase()
        );
    });

    // Should show dropdown
    let shouldShowDropdown = $derived.by(() => {
        return showDropdown && (filteredDimensions.length > 0 || (searchInput.trim() && !existingDimension));
    });

    function handleInputFocus() {
        showDropdown = true;
        activeIndex = 0;
    }

    function handleInputBlur() {
        // Delay hiding to allow click events
        setTimeout(() => {
            showDropdown = false;
        }, 200);
    }

    function handleInput() {
        showDropdown = true;
        activeIndex = 0;

        // Debounce search with 300ms delay
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }

        debounceTimer = setTimeout(() => {
            // Update parent value as user types (after debounce)
            onChange(searchInput);
        }, 300);
    }

    function selectDimension(dimension: Dimension) {
        onChange(dimension.id);
        searchInput = dimension.label;
        showDropdown = false;
    }

    function createNewDimension() {
        if (searchInput.trim() && onCreateNew) {
            onCreateNew(searchInput.trim());
            searchInput = "";
            showDropdown = false;
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            showDropdown = false;
            event.preventDefault();
        } else if (event.key === "ArrowDown") {
            if (showDropdown) {
                event.preventDefault();
                const maxIndex = filteredDimensions.length + (searchInput.trim() && !existingDimension ?1 : 0) - 1;
                activeIndex = Math.min(activeIndex + 1, maxIndex);
            }
        } else if (event.key === "ArrowUp") {
            if (showDropdown) {
                event.preventDefault();
                activeIndex = Math.max(activeIndex - 1, 0);
            }
        } else if (event.key === "Enter") {
            if (showDropdown) {
                event.preventDefault();
                // Select from list or create new
                if (activeIndex < filteredDimensions.length) {
                    selectDimension(filteredDimensions[activeIndex]);
                } else if (searchInput.trim() && onCreateNew) {
                    createNewDimension();
                }
            }
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            showDropdown = false;
        }
    }

    // Handle click outside to close dropdown
    $effect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef && !containerRef.contains(event.target as Node)) {
                showDropdown = false;
            }
        }

        if (showDropdown) {
            document.addEventListener("click", handleClickOutside);
        }

        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    });

    // Cleanup debounce timer on unmount
    $effect(() => {
        return () => {
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }
        };
    });

    // Initialize searchInput with current value's label if dimension exists
    $effect(() => {
        if (value) {
            const dimension = dimensions.find((d) => d.id === value);
            if (dimension && !searchInput) {
                searchInput = dimension.label;
            }
        }
    });

    // Reset searchInput when value changes externally
    $effect(() => {
        if (value !== searchInput && !showDropdown) {
            const dimension = dimensions.find((d) => d.id === value);
            searchInput = dimension?.label || value || "";
        }
    });
</script>

<div class="relative">
<div class="relative" bind:this={containerRef}>
        <input
            type="text"
            bind:value={searchInput}
            onfocus={handleInputFocus}
            onblur={handleInputBlur}
            oninput={handleInput}
            onkeydown={handleKeydown}
            {placeholder}
            disabled={disabled || loading}
            class="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
        />
        {#if loading}
            <Icon icon="lucide:loader-2" class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 animate-spin" />
        {:else}
            <Icon icon="lucide:search" class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        {/if}
    </div>

    {#if shouldShowDropdown}
        <div
            class="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto"
            onmousedown={(e) => e.preventDefault()}
        >
            <!-- Existing dimensions -->
            {#each filteredDimensions as dimension, index}
                <button
                    type="button"
                    class="w-full text-left px-3 py-2 text-sm hover:bg-blue-50 focus:bg-blue-50 focus:outline-none {index === activeIndex ? 'bg-blue-50' : ''}"
                    onmousedown={() => selectDimension(dimension)}
                    onkeydown={(e) => e.key === 'Enter' && selectDimension(dimension)}
                >
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="font-medium text-gray-900">{dimension.label}</span>
                            <span class="text-xs text-gray-500 font-mono">{dimension.id}</span>
                        </div>
                        {#if dimension.annotation_type}
                            <span class="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                                {dimension.annotation_type}
                            </span>
                        {/if}
                    </div>
                </button>
            {/each}

            <!-- Create new option -->
            {#if searchInput.trim() && !existingDimension && onCreateNew}
                <button
                    type="button"
                    class="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 focus:bg-blue-50 focus:outline-none border-t border-gray-200"
                    onmousedown={createNewDimension}
                    onkeydown={(e) => e.key === 'Enter' && createNewDimension()}
                >
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:plus-circle" class="w-4 h-4" />
                        <span>Create new dimension: <strong>"{searchInput}"</strong></span>
                    </div>
                </button>
            {/if}
        </div>
    {/if}
</div>
