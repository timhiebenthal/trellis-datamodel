<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { Dimension, SevenWType } from "$lib/types";

    type Props = {
        textValue: string;
        onTextChange: (value: string) => void;
        onSelectDimension?: (dimension: Dimension) => void;
        dimensions: Dimension[];
        filterBy?: SevenWType;
        allowedIds?: Set<string> | null;
        onCreateNew?: (text: string) => void;
        disabled?: boolean;
        placeholder?: string;
        loading?: boolean;
    };

    let {
        textValue,
        onTextChange,
        onSelectDimension,
        dimensions,
        filterBy,
        allowedIds = null,
        onCreateNew,
        disabled = false,
        placeholder = "Select or create dimension...",
        loading = false,
    }: Props = $props();

    let showDropdown = $state(false);
    let searchInput = $state("");
    let activeIndex = $state(0);
    let containerRef = $state<HTMLDivElement>();
    let inputRef = $state<HTMLInputElement>();
    let dropdownStyle = $state("");

    // Computed filtered dimensions
    let filteredDimensions = $derived.by(() => {
        return dimensions.filter((d) => {
            if (allowedIds && !allowedIds.has(d.id)) {
                return false;
            }
            // Filter by annotation_type if specified.
            // If dimension lacks annotation_type, allow it (backwards compatibility).
            if (filterBy && d.annotation_type && d.annotation_type !== filterBy) {
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
        onTextChange(searchInput);
    }

    function selectDimension(dimension: Dimension) {
        searchInput = dimension.label;
        onTextChange(dimension.label);
        if (onSelectDimension) {
            onSelectDimension(dimension);
        }
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

    function updateDropdownPosition() {
        if (!inputRef) return;
        const rect = inputRef.getBoundingClientRect();
        dropdownStyle = `position:fixed;left:${rect.left}px;top:${rect.bottom + 4}px;width:${rect.width}px;z-index:60;`;
    }

    $effect(() => {
        if (!showDropdown) return;
        updateDropdownPosition();
        const handleReposition = () => updateDropdownPosition();
        window.addEventListener("resize", handleReposition);
        window.addEventListener("scroll", handleReposition, true);
        return () => {
            window.removeEventListener("resize", handleReposition);
            window.removeEventListener("scroll", handleReposition, true);
        };
    });


    // Keep internal input in sync with parent value.
    $effect(() => {
        if (!showDropdown && textValue !== searchInput) {
            searchInput = textValue || "";
        }
    });
</script>

<div class="relative" bind:this={containerRef}>
        <input
            type="text"
            bind:value={searchInput}
            bind:this={inputRef}
            onfocus={handleInputFocus}
            onblur={handleInputBlur}
            oninput={handleInput}
            onkeydown={handleKeydown}
            {placeholder}
            disabled={disabled || loading}
            class="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
        />
        {#if loading}
            <Icon icon="lucide:loader-2" data-icon="lucide:loader-2" class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 animate-spin" />
        {:else}
            <Icon icon="lucide:search" class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        {/if}
    {#if shouldShowDropdown}
        <div
            class="bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto"
            style={dropdownStyle}
            onmousedown={(e) => e.preventDefault()}
            role="listbox"
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