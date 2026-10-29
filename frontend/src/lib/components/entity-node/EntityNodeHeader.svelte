<script lang="ts">
    import Icon from "@iconify/svelte";
    import { goto } from "$app/navigation";
    import {
        viewMode,
        exposureEntityFilter,
        openDeleteConfirmModal,
        openLineageModal,
    } from "$lib/stores";
    import type { EntityNodeData } from "$lib/types";
    import { getEntityTypeStyle } from "$lib/utils/entity-type-style";

    type EntityType = "fact" | "dimension" | "unclassified";

    let {
        id,
        data,
        isCollapsed,
        isBound,
        boundModelName,
        isDimensionalModeling,
        lineageEnabled,
        exposuresEnabled,
        hasExposuresData,
        unboundHint,
        onToggleCollapse,
        onLabelFocus,
        onLabelInput,
        onLabelBlur,
        onSetEntityType,
    }: {
        id: string;
        data: EntityNodeData;
        isCollapsed: boolean;
        isBound: boolean;
        boundModelName: string | undefined;
        isDimensionalModeling: boolean;
        lineageEnabled: boolean;
        exposuresEnabled: boolean;
        hasExposuresData: boolean;
        unboundHint: string;
        onToggleCollapse: () => void;
        onLabelFocus: () => void;
        onLabelInput: (e: Event) => void;
        onLabelBlur: (e: Event) => void;
        onSetEntityType: (newType: EntityType) => void;
    } = $props();

    let showEntityTypeMenu = $state(false);

    function openExposuresView(event: MouseEvent) {
        event.stopPropagation(); // Prevent collapse toggle
        exposureEntityFilter.set(id);
        viewMode.set('exposures');
        goto('/exposures');
    }

    function handleLineageClick(event: MouseEvent) {
        event.stopPropagation();
        if (boundModelName) {
            openLineageModal(boundModelName);
        }
    }

    function toggleCollapse(event: Event) {
        // Only toggle if clicking on the header background, not on the input
        if ((event.target as HTMLElement).tagName === "INPUT") {
            return;
        }
        onToggleCollapse();
    }

    function handleHeaderKeydown(event: KeyboardEvent) {
        // Only handle keyboard events if the target is not an input field
        if ((event.target as HTMLElement).tagName === "INPUT") {
            return;
        }
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            toggleCollapse(event);
        }
    }

    function handleDeleteClick(event: MouseEvent) {
        event.stopPropagation(); // Prevent collapse toggle
        openDeleteConfirmModal(data.label || "Entity", [id]);
    }

    // Entity type menu functionality
    function toggleEntityTypeMenu() {
        showEntityTypeMenu = !showEntityTypeMenu;
    }

    function closeEntityTypeMenu() {
        showEntityTypeMenu = false;
    }

    async function setEntityType(newType: EntityType) {
        try {
            // Update node data locally
            onSetEntityType(newType);
            closeEntityTypeMenu();
        } catch (error) {
            console.error("Failed to update entity type:", error);
            alert("Failed to update entity type. Please try again.");
        }
    }
</script>

<!-- Header -->
<div
    class="p-2.5 border-b border-gray-100 bg-gray-50/50 rounded-t-lg flex justify-between items-center cursor-pointer hover:bg-gray-50 transition-colors"
    onclick={toggleCollapse}
    onkeydown={handleHeaderKeydown}
    role="button"
    tabindex="0"
    title={isCollapsed ? "Click to expand" : "Click to collapse"}
>
    <div class="flex items-center gap-2 flex-1 min-w-0">
        <span
            class="text-gray-400 text-[10px] flex-shrink-0 select-none transition-transform duration-200"
        >
            {#if isCollapsed}
                <Icon icon="lucide:chevron-right" class="w-4 h-4" />
            {:else}
                <Icon icon="lucide:chevron-down" class="w-4 h-4" />
            {/if}
        </span>
        <!-- Entity Type Badge (only shown in dimensional_model mode) -->
        {#if isDimensionalModeling && data.entity_type}
            <button
                type="button"
                class="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 border-0 cursor-pointer {getEntityTypeStyle(data.entity_type).badge}"
                class:opacity-80={true}
                onclick={(e) => { e.stopPropagation(); toggleEntityTypeMenu(); }}
                title={data.entity_type === 'fact'
                    ? 'Fact: Transaction table containing measures and keys (click to change)'
                    : data.entity_type === 'dimension'
                    ? 'Dimension: Descriptive table with attributes (click to change)'
                    : 'Unclassified: Generic entity (click to change)'}
            >
                <Icon
                    icon={getEntityTypeStyle(data.entity_type).icon}
                    class="w-3 h-3"
                />
            </button>
        {/if}
        <input
            type="text"
            value={data.label}
            onfocus={onLabelFocus}
            oninput={onLabelInput}
            onblur={onLabelBlur}
            onclick={(e) => e.stopPropagation()}
            ondblclick={(e) => e.stopPropagation()}
            onkeydown={(e) => e.stopPropagation()}
            onkeyup={(e) => e.stopPropagation()}
            class="font-bold inline-input bg-transparent focus:outline-none focus:bg-white focus:ring-1 focus:ring-primary-500 rounded px-1.5 py-0.5 text-sm min-w-0 max-w-full flex-shrink"
            style={`width: ${Math.max((data.label?.length ?? 0) + 2, 8)}ch`}
            placeholder="Entity Name"
        />
    </div>
    <div class="flex items-center gap-2 flex-shrink-0">
        {#if isBound}
            <div
                class="w-2 h-2 rounded-full bg-primary-500"
                title="Bound to {boundModelName}"
            ></div>
            {#if lineageEnabled && boundModelName}
                <button
                    onclick={handleLineageClick}
                    aria-label="Show lineage for {boundModelName}"
                    class="text-gray-400 hover:text-primary-600 transition-colors px-1.5 py-0.5 rounded hover:bg-primary-50 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    title="Show lineage"
                >
                    <Icon icon="lucide:git-branch" class="w-4 h-4" />
                </button>
            {/if}
            {#if exposuresEnabled && hasExposuresData}
                <button
                    onclick={openExposuresView}
                    aria-label="Show exposures for {data.label}"
                    class="text-gray-400 hover:text-primary-600 transition-colors px-1.5 py-0.5 rounded hover:bg-primary-50 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    title="Show exposures"
                >
                    <Icon icon="mdi:application-export" class="w-4 h-4" />
                </button>
            {/if}
        {:else}
            <div
                class="w-2 h-2 rounded-full bg-amber-500"
                title={unboundHint}
            ></div>
            {#if exposuresEnabled && hasExposuresData}
                <button
                    onclick={openExposuresView}
                    aria-label="Show exposures for {data.label}"
                    class="text-gray-400 hover:text-primary-600 transition-colors px-1.5 py-0.5 rounded hover:bg-primary-50 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    title="Show exposures"
                >
                    <Icon icon="mdi:application-export" class="w-4 h-4" />
                </button>
            {/if}
        {/if}
        <button
            onclick={handleDeleteClick}
            aria-label="Delete entity {data.label}"
            class="text-gray-400 hover:text-danger-600 transition-colors px-1.5 py-0.5 rounded hover:bg-danger-50 focus:outline-none focus:ring-1 focus:ring-danger-500"
            title="Delete entity"
        >
            <Icon icon="lucide:x" class="w-4 h-4" />
        </button>
    </div>
</div>

<!-- Entity Type Dropdown Menu (only shown in dimensional_model mode) -->
{#if showEntityTypeMenu && isDimensionalModeling}
    <div
        class="absolute z-50 bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[140px] text-sm transition-all duration-200 ease-in-out"
        style="top: 45px; right: 10px;"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
        onfocusout={() => {
            // Allow focus to move to menu items before closing
            queueMicrotask(() => {
                const focused = document.activeElement;
                const container = focused?.closest('[role="menu"]');
                if (!container) {
                    closeEntityTypeMenu();
                }
            });
        }}
        role="menu"
        tabindex="-1"
    >
        <button
            onclick={() => setEntityType('fact')}
            class="w-full px-3 py-2 flex items-center gap-2 hover:bg-blue-50 text-left transition-colors"
            role="menuitem"
        >
            <Icon icon={getEntityTypeStyle('fact').icon} class="w-4 h-4 {getEntityTypeStyle('fact').iconClass}" />
            <span class="text-gray-700">Set as Fact</span>
        </button>
        <button
            onclick={() => setEntityType('dimension')}
            class="w-full px-3 py-2 flex items-center gap-2 hover:bg-green-50 text-left transition-colors"
            role="menuitem"
        >
            <Icon icon={getEntityTypeStyle('dimension').icon} class="w-4 h-4 {getEntityTypeStyle('dimension').iconClass}" />
            <span class="text-gray-700">Set as Dimension</span>
        </button>
        <button
            onclick={() => setEntityType('unclassified')}
            class="w-full px-3 py-2 flex items-center gap-2 hover:bg-gray-50 text-left transition-colors"
            role="menuitem"
        >
            <Icon icon={getEntityTypeStyle('unclassified').icon} class="w-4 h-4 {getEntityTypeStyle('unclassified').iconClass}" />
            <span class="text-gray-700">Set as Unclassified</span>
        </button>
    </div>
{/if}
