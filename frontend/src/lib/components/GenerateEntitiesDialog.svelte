<script lang="ts">
    import { generateEntitiesFromEvent, updateBusinessEvent } from '$lib/api';
    import type { BusinessEvent, GeneratedEntitiesResult } from '$lib/types';
    import { nodes, edges, modelingStyle } from '$lib/stores';
    import { generateSlug, mergeRelationshipIntoEdges } from '$lib/utils';
    import { DimensionalModelPositioner } from '$lib/services/position-calculator';
    import type { Node, Edge } from '@xyflow/svelte';
    import Icon from '@iconify/svelte';

    type Props = {
        open: boolean;
        event: BusinessEvent | null;
        onConfirm: () => void;
        onCancel: () => void;
    };

    let { open, event, onConfirm, onCancel }: Props = $props();

    let loading = $state(false);
    let error = $state<string | null>(null);
    let previewData = $state<GeneratedEntitiesResult | null>(null);
    let editedEntities = $state<Array<{ id: string; label: string; entity_type: string; tags?: string[] }>>([]);
    let validationErrors = $state<string[]>([]);
    let creating = $state(false);
    let success = $state(false);

    const positioner = new DimensionalModelPositioner();

    // Load preview data when dialog opens
    $effect(() => {
        if (open && event) {
            loadPreview();
        } else {
            // Reset state when dialog closes
            previewData = null;
            editedEntities = [];
            validationErrors = [];
            error = null;
            success = false;
        }
    });

    async function loadPreview() {
        if (!event) return;

        try {
            loading = true;
            error = null;
            previewData = await generateEntitiesFromEvent(event.id);
            // Initialize edited entities with preview data (including tags)
            editedEntities = previewData.entities.map((e) => ({
                id: e.id,
                label: e.label,
                entity_type: e.entity_type,
                tags: e.tags || [],
            }));
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to generate preview';
            console.error('Error generating preview:', error);
        } finally {
            loading = false;
        }
    }

    function updateEntityName(index: number, name: string) {
        editedEntities[index] = { ...editedEntities[index], id: name };
        validateEntities();
    }

    function updateEntityLabel(index: number, label: string) {
        editedEntities[index] = { ...editedEntities[index], label };
        validateEntities();
    }

    function validateEntities(): void {
        validationErrors = [];

        // Check for at least 1 dimension and 1 fact
        const dimensions = editedEntities.filter((e) => e.entity_type === 'dimension');
        const facts = editedEntities.filter((e) => e.entity_type === 'fact');
        
        if (dimensions.length === 0) {
            validationErrors.push('At least one dimension is required');
        }
        if (facts.length === 0) {
            validationErrors.push('At least one fact is required');
        }

        // Check for empty names
        for (let i = 0; i < editedEntities.length; i++) {
            if (!editedEntities[i].id || !editedEntities[i].id.trim()) {
                validationErrors.push(`Entity ${i + 1} name cannot be empty`);
            }
        }

        // Check for duplicate names
        const nameCounts = new Map<string, number>();
        for (let i = 0; i < editedEntities.length; i++) {
            const name = editedEntities[i].id.trim();
            if (name) {
                nameCounts.set(name, (nameCounts.get(name) || 0) + 1);
            }
        }

        for (const [name, count] of nameCounts.entries()) {
            if (count > 1) {
                validationErrors.push(`Duplicate entity name: "${name}"`);
            }
        }

        // Check against existing canvas entities
        const existingIds = $nodes.filter((n) => n.type === 'entity').map((n) => n.id);
        for (let i = 0; i < editedEntities.length; i++) {
            const name = editedEntities[i].id.trim();
            if (name && existingIds.includes(name)) {
                validationErrors.push(`Entity name "${name}" already exists on canvas. Please rename it (e.g., "${name}_v2")`);
            }
        }
    }

    async function handleCreateAll() {
        if (!previewData || !event) return;

        validateEntities();
        if (validationErrors.length > 0) {
            return;
        }

        try {
            creating = true;
            error = null;

            // Create entities on canvas
            const createdEntityIds: string[] = [];
            const maxZIndex = Math.max(
                ...$nodes.map((n) => n.zIndex || (n.type === 'group' ? 1 : 10)),
                10
            );

            for (let i = 0; i < editedEntities.length; i++) {
                const edited = editedEntities[i];
                const original = previewData.entities[i];

                // Generate unique ID
                const id = generateSlug(edited.id.trim(), [
                    ...$nodes.map((n) => n.id),
                    ...createdEntityIds,
                ]);

                // Calculate position based on entity type
                let position: { x: number; y: number };
                if ($modelingStyle === 'dimensional_model' && edited.entity_type) {
                    position = positioner.calculateSmartPosition(
                        edited.entity_type as 'fact' | 'dimension' | 'unclassified',
                        $nodes
                    );
                } else {
                    position = {
                        x: 100 + Math.random() * 200,
                        y: 100 + Math.random() * 200,
                    };
                }

                // Create node (include tags from preview data)
                const newNode: Node = {
                    id,
                    type: 'entity',
                    position,
                    data: {
                        label: edited.label.trim() || edited.id.trim(),
                        description: original.description || '',
                        entity_type: edited.entity_type,
                        tags: original.tags || [],
                        width: 280,
                        panelHeight: 200,
                        collapsed: false,
                    },
                    zIndex: maxZIndex + i + 1,
                };

                $nodes = [...$nodes, newNode];
                createdEntityIds.push(id);
            }

            // Create relationships
            if (previewData.relationships && previewData.relationships.length > 0) {
                // Map original entity IDs to created entity IDs
                const idMapping = new Map<string, string>();
                for (let i = 0; i < previewData.entities.length; i++) {
                    const originalId = previewData.entities[i].id;
                    const createdId = createdEntityIds[i];
                    idMapping.set(originalId, createdId);
                }

                // Create edges for relationships
                for (const rel of previewData.relationships) {
                    const sourceId = idMapping.get(rel.source) || rel.source;
                    const targetId = idMapping.get(rel.target) || rel.target;

                    // Only create relationship if both entities exist
                    if (
                        createdEntityIds.includes(sourceId) &&
                        createdEntityIds.includes(targetId)
                    ) {
                        const relationship = {
                            source: sourceId,
                            target: targetId,
                            label: rel.label || '',
                            type: rel.type || 'one_to_many',
                        };
                        $edges = mergeRelationshipIntoEdges($edges, relationship);
                    }
                }
            }

            // Update event's derived_entities list
            const derivedEntities = createdEntityIds.map((id) => ({
                entity_id: id,
                created_at: new Date().toISOString(),
            }));

            await updateBusinessEvent(event.id, {
                derived_entities: derivedEntities,
            });

            success = true;
            // Close dialog after a short delay
            setTimeout(() => {
                onConfirm();
            }, 1500);
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to create entities';
            console.error('Error creating entities:', error);
        } finally {
            creating = false;
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            onCancel();
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onCancel();
        }
    }

    // Validate on entity changes
    $effect(() => {
        if (editedEntities.length > 0) {
            validateEntities();
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
        aria-labelledby="generate-entities-dialog-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            role="document"
            tabindex="-1"
            onclick={(e) => e.stopPropagation()}
        >
            <div class="flex items-center justify-between mb-4">
                <h2
                    id="generate-entities-dialog-title"
                    class="text-xl font-semibold text-gray-900"
                >
                    Generate Entities from Event
                </h2>
                <button
                    onclick={onCancel}
                    class="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                    title="Close"
                >
                    <Icon icon="lucide:x" class="w-5 h-5" />
                </button>
            </div>

            {#if loading}
                <div class="flex items-center justify-center py-12">
                    <div class="text-center">
                        <div class="w-8 h-8 animate-spin border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-2"></div>
                        <p class="text-sm text-gray-600">Generating preview...</p>
                    </div>
                </div>
            {:else if error}
                <div class="bg-red-50 border border-red-200 rounded p-4 mb-4">
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:alert-circle" class="w-5 h-5 text-red-600" />
                        <p class="text-sm text-red-800">{error}</p>
                    </div>
                </div>
                <div class="flex justify-end gap-2">
                    <button
                        onclick={onCancel}
                        class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                        Close
                    </button>
                </div>
            {:else if success}
                <div class="bg-green-50 border border-green-200 rounded p-4 mb-4">
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:check-circle" class="w-5 h-5 text-green-600" />
                        <p class="text-sm text-green-800">Entities created successfully!</p>
                    </div>
                </div>
            {:else if previewData && editedEntities.length > 0}
                <div class="space-y-4">
                    <!-- Validation Errors -->
                    {#if validationErrors.length > 0}
                        <div class="bg-red-50 border border-red-200 rounded p-4">
                            <div class="flex items-start gap-2">
                                <Icon icon="lucide:alert-triangle" class="w-5 h-5 text-red-600 mt-0.5" />
                                <div class="flex-1">
                                    <p class="text-sm font-medium text-red-800 mb-1">Validation Errors:</p>
                                    <ul class="text-sm text-red-700 list-disc list-inside">
                                        {#each validationErrors as err}
                                            <li>{err}</li>
                                        {/each}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    {/if}

                    <!-- Domain Tag Note -->
                    {#if event?.domain}
                        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                            <div class="flex items-start gap-2">
                                <Icon icon="lucide:info" class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                                <p class="text-sm text-blue-800">
                                    <strong>Domain Tag:</strong> All entities will inherit the "<span class="font-mono font-semibold">{event.domain}</span>" tag from this event.
                                </p>
                            </div>
                        </div>
                    {/if}

                    <!-- Entities Table -->
                    <div class="border border-gray-200 rounded-lg overflow-hidden">
                        <table class="w-full">
                            <thead class="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                        Entity Type
                                    </th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                        Name
                                    </th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                        Label
                                    </th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                        Tags
                                    </th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                {#each editedEntities as entity, index}
                                    <tr class="hover:bg-gray-50">
                                        <td class="px-4 py-3">
                                            <span
                                                class="px-2 py-1 text-xs font-medium rounded {entity.entity_type === 'dimension'
                                                    ? 'bg-blue-100 text-blue-800'
                                                    : entity.entity_type === 'fact'
                                                      ? 'bg-green-100 text-green-800'
                                                      : 'bg-gray-100 text-gray-800'}"
                                            >
                                                {entity.entity_type === 'dimension'
                                                    ? 'Dimension'
                                                    : entity.entity_type === 'fact'
                                                      ? 'Fact'
                                                      : 'Unclassified'}
                                            </span>
                                        </td>
                                        <td class="px-4 py-3">
                                            <input
                                                type="text"
                                                value={entity.id}
                                                oninput={(e) =>
                                                    updateEntityName(
                                                        index,
                                                        (e.target as HTMLInputElement).value
                                                    )}
                                                class="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                                placeholder="Entity name"
                                            />
                                        </td>
                                        <td class="px-4 py-3">
                                            <input
                                                type="text"
                                                value={entity.label}
                                                oninput={(e) =>
                                                    updateEntityLabel(
                                                        index,
                                                        (e.target as HTMLInputElement).value
                                                    )}
                                                class="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                                placeholder="Display label"
                                            />
                                        </td>
                                        <td class="px-4 py-3">
                                            {#if previewData.entities[index]?.tags && previewData.entities[index].tags!.length > 0}
                                                <div class="flex flex-wrap gap-1">
                                                    {#each previewData.entities[index].tags! as tag}
                                                        <span
                                                            class="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200 font-mono"
                                                            title="Inherited tag from event domain"
                                                        >
                                                            {tag}
                                                        </span>
                                                    {/each}
                                                </div>
                                            {:else}
                                                <span class="text-xs text-gray-400">—</span>
                                            {/if}
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>

                    <!-- Relationships Section -->
                    {#if previewData.relationships && previewData.relationships.length > 0}
                        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                            <h3 class="text-sm font-medium text-gray-700 mb-2">Relationships:</h3>
                            <div class="space-y-1">
                                {#each previewData.relationships as rel}
                                    <p class="text-sm text-gray-600">
                                        <span class="font-mono">{rel.source}</span>
                                        <span class="mx-2">→</span>
                                        <span class="font-mono">{rel.target}</span>
                                        {#if rel.label}
                                            <span class="text-gray-500 ml-2">({rel.label})</span>
                                        {/if}
                                    </p>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Actions -->
                    <div class="flex justify-end gap-2 pt-4 border-t border-gray-200">
                        <button
                            onclick={onCancel}
                            class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
                            disabled={creating}
                        >
                            Cancel
                        </button>
                        <button
                            onclick={handleCreateAll}
                            class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                            disabled={creating || validationErrors.length > 0}
                        >
                            {#if creating}
                                <div class="w-4 h-4 animate-spin border-2 border-white border-t-transparent rounded-full"></div>
                                <span>Creating...</span>
                            {:else}
                                <Icon icon="lucide:sparkles" class="w-4 h-4" />
                                <span>Create All</span>
                            {/if}
                        </button>
                    </div>
                </div>
            {:else}
                <div class="text-center py-8 text-gray-500">
                    <p>No entities to generate. Please add annotations to the event first.</p>
                </div>
                <div class="flex justify-end gap-2 pt-4">
                    <button
                        onclick={onCancel}
                        class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                        Close
                    </button>
                </div>
            {/if}
        </div>
    </div>
{/if}
