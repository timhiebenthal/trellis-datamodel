<script lang="ts">
    import Icon from "@iconify/svelte";

    type EntityWithUndescribedAttributes = {
        entityLabel: string;
        entityId: string;
        attributeNames: string[];
    };

    type Props = {
        open: boolean;
        attributeNames?: string[]; // For single entity (Save to YAML)
        entitiesWithAttributes?: EntityWithUndescribedAttributes[]; // For multiple entities (Push to dbt)
        onConfirm: () => void;
        onCancel: () => void;
    };

    let { open, attributeNames, entitiesWithAttributes, onConfirm, onCancel }: Props = $props();

    // Determine if we're showing single entity or multiple entities
    let isMultipleEntities = $derived(!!entitiesWithAttributes && entitiesWithAttributes.length > 0);
    let totalAttributes = $derived(
        isMultipleEntities
            ? entitiesWithAttributes!.reduce((sum, e) => sum + e.attributeNames.length, 0)
            : (attributeNames?.length || 0)
    );

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

    function handleConfirm() {
        onConfirm();
    }

    let collapsedEntities = $state(new Set<string>());

    function toggleEntity(entityId: string) {
        const next = new Set(collapsedEntities);
        if (next.has(entityId)) {
            next.delete(entityId);
        } else {
            next.add(entityId);
        }
        collapsedEntities = next;
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
        aria-labelledby="warning-modal-title"
    >
        <!-- Modal Content -->
        <div
            class="bg-white rounded-lg shadow-xl p-8 max-w-lg w-full mx-4"
            role="document"
            tabindex="-1"
            aria-label="Warning about attributes without descriptions"
        >
            <div class="flex items-start gap-3 mb-6">
                <div class="flex-shrink-0">
                    <Icon icon="lucide:alert-triangle" class="w-6 h-6 text-amber-600" />
                </div>
                <div class="flex-1">
                    <h2 id="warning-modal-title" class="text-xl font-semibold text-gray-900 mb-3">
                        ⚠️ Attributes Without Descriptions
                    </h2>
                    <p class="text-sm text-gray-600 mb-6">
                        {#if isMultipleEntities}
                            {entitiesWithAttributes!.length} {entitiesWithAttributes!.length === 1 ? 'entity has' : 'entities have'} {totalAttributes} {totalAttributes === 1 ? 'attribute' : 'attributes'} without descriptions.
                        {:else}
                            {totalAttributes} {totalAttributes === 1 ? 'attribute is' : 'attributes are'} missing descriptions.
                        {/if}
                        They will be saved without descriptions.
                    </p>
                </div>
            </div>

            <!-- Attribute List -->
            {#if isMultipleEntities}
                <!-- Multiple entities view -->
                <div class="mb-6 max-h-96 overflow-y-auto border border-gray-200 rounded-md">
                    {#each entitiesWithAttributes! as entity}
                        {@const collapsed = collapsedEntities.has(entity.entityId)}
                        <div class="border-b border-gray-200 last:border-b-0">
                            <button
                                class="w-full flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 text-left transition-colors"
                                onclick={() => toggleEntity(entity.entityId)}
                                aria-expanded={!collapsed}
                            >
                                <Icon
                                    icon="lucide:chevron-down"
                                    class="w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform {collapsed ? '-rotate-90' : ''}"
                                />
                                <span class="font-medium text-gray-900">{entity.entityLabel}</span>
                                {#if entity.entityId !== entity.entityLabel}
                                    <span class="text-gray-500 text-xs">({entity.entityId})</span>
                                {/if}
                                <span class="text-gray-400 text-xs ml-auto">
                                    {entity.attributeNames.length} {entity.attributeNames.length === 1 ? 'attribute' : 'attributes'}
                                </span>
                            </button>
                            {#if !collapsed}
                                <ul class="divide-y divide-gray-100">
                                    {#each entity.attributeNames as attributeName}
                                        <li class="px-3 py-1.5 text-sm pl-8">
                                            <span class="font-mono text-gray-700">{attributeName}</span>
                                        </li>
                                    {/each}
                                </ul>
                            {/if}
                        </div>
                    {/each}
                </div>
            {:else if attributeNames && attributeNames.length > 0}
                <!-- Single entity view -->
                <div class="mb-6 max-h-48 overflow-y-auto border border-gray-200 rounded-md">
                    <ul class="divide-y divide-gray-200">
                        {#each attributeNames as attributeName}
                            <li class="px-3 py-2 text-sm">
                                <span class="font-medium text-gray-900 font-mono">{attributeName}</span>
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            <!-- Actions -->
            <div class="flex justify-end gap-4">
                <button
                    onclick={onCancel}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                    Cancel
                </button>
                <button
                    onclick={handleConfirm}
                    class="px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded-md hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500"
                >
                    Continue Anyway
                </button>
            </div>
        </div>
    </div>
{/if}

