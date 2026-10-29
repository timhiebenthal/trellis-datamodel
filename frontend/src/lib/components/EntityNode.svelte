<script lang="ts">
    import {
        Handle,
        Position,
        useSvelteFlow,
        type NodeProps,
    } from "@xyflow/svelte";
    import {
        viewMode,
        frameworkModels,
        nodes,
        edges,
        modelingStyle,
        labelPrefixes,
        dimensionPrefixes,
        factPrefixes,
        sourceColors,
        openSourceEditorModal,
        closeDeleteConfirmModal,
        activeFramework,
    } from "$lib/stores";
    import type { ModelInfo, DraftedField, EntityFlowNode } from "$lib/types";
    import { isEntityNode } from "$lib/types";
    import { inferRelationships } from "$lib/api";
    import { generateSlug } from "$lib/utils/slug";
    import { mergeRelationshipIntoEdges } from "$lib/utils/relationship-edges";
    import { formatModelNameForLabel, extractModelNameFromUniqueId, toTitleCase, classifyModelTypeFromPrefixes } from "$lib/utils/model-naming";
    import { normalizeTags, computeUiTagsAfterEdit } from "$lib/utils/entity-tags";
    import { getFrameworkCopy } from "$lib/utils/framework-display";
    import { readModelRef, readFrameworkTags } from "$lib/utils/entity-compat";
    import {
        buildModelToEntityMap,
        modelShortName as getModelShortName,
        remapInferredRelationships,
        renameNode,
        renameNodeInEdges,
    } from "$lib/utils/entity-binding";
    import { getSourceChipStyle } from "$lib/utils/source-chip-style";
    import { uniqueRoleNames } from "$lib/utils/entity-roles";
    import {
        DEFAULT_NODE_WIDTH,
        DEFAULT_PANEL_HEIGHT,
        computeResizePatch,
        type ResizeDimension,
    } from "$lib/utils/node-dimensions";
    import { getContext } from "svelte";
    import Icon from "@iconify/svelte";
    import { readable, type Readable } from "svelte/store";
    import { SchemaManager, type SchemaState } from "$lib/services/schema-manager";
    import EntityNodeHeader from "./entity-node/EntityNodeHeader.svelte";
    import EntityNodeFields from "./entity-node/EntityNodeFields.svelte";
    import EntityNodeTags from "./entity-node/EntityNodeTags.svelte";
    import EntityNodeRoles from "./entity-node/EntityNodeRoles.svelte";
    import BatchEditBanner from "./entity-node/BatchEditBanner.svelte";

    let { data, id, selected }: NodeProps<EntityFlowNode> = $props();

    const { updateNodeData } = useSvelteFlow();
    // Delete and SourceEditor modals are rendered at page-level (outside SvelteFlow) via global stores

    // Batch editing support
    let selectedEntityNodes = $derived(
        $nodes.filter((n) => n.selected && n.type === "entity" && n.id !== id)
    );
    let isBatchEditing = $derived(selected && selectedEntityNodes.length > 0);

    const lineageEnabledStore =
        getContext<Readable<boolean>>("lineageEnabled") ?? readable(false);
    let lineageEnabled = $derived($lineageEnabledStore);

    const exposuresEnabledStore =
        getContext<Readable<boolean>>("exposuresEnabled") ?? readable(false);
    let exposuresEnabled = $derived($exposuresEnabledStore);

    // Entity type controls only for dimensional modeling
    let isDimensionalModeling = $derived($modelingStyle === "dimensional_model");

    const hasExposuresDataStore =
        getContext<Readable<boolean>>("hasExposuresData") ?? readable(false);
    let hasExposuresData = $derived($hasExposuresDataStore);

    // Reactive binding check
    let boundModelName = $derived(readModelRef(data));
    let additionalModels = $derived((data.additional_models as string[]) || []);
    let allBoundModels = $derived(
        boundModelName ? [boundModelName, ...additionalModels] : []
    );
    let activeModelIndex = $state(0); // ephemeral, defaults to primary
    let activeModelId = $derived(allBoundModels[activeModelIndex] || boundModelName);
    let isBound = $derived(!!boundModelName);
    let isCollapsed = $derived(data.collapsed ?? false);
    let frameworkCopy = $derived(getFrameworkCopy($activeFramework));
    let nodeWidth = $derived(data.width ?? DEFAULT_NODE_WIDTH);
    let columnPanelHeight = $derived(data.panelHeight ?? DEFAULT_PANEL_HEIGHT);
    // Find model details by unique_id (e.g. "model.elmo.entity_booking")
    let modelDetails = $derived(
        activeModelId ? $frameworkModels.find((m) => m.unique_id === activeModelId) : null,
    );

    // Reset active index when models change
    $effect(() => {
        if (allBoundModels.length > 0 && activeModelIndex >= allBoundModels.length) {
            activeModelIndex = 0;
        }
    });

    // Reset to primary model when switching to logical view
    let previousViewMode = $state<'conceptual' | 'logical' | 'exposures'>('conceptual');
    $effect(() => {
        const currentViewMode = $viewMode;
        // Only reset when switching FROM conceptual TO logical (ignore exposures mode)
        if (previousViewMode === "conceptual" && currentViewMode === "logical" && allBoundModels.length > 0) {
            activeModelIndex = 0;
        }
        // Only track conceptual/logical modes for this logic
        if (currentViewMode === "conceptual" || currentViewMode === "logical") {
            previousViewMode = currentViewMode;
        }
    });

    // Schema management using SchemaManager service
    let schemaManager: SchemaManager | null = null;
    let schemaState: SchemaState = $state({
        editableColumns: [],
        isLoading: false,
        isSaving: false,
        error: null,
        hasUnsavedChanges: false,
        schema: null,
        schemaTags: [],
        manifestTags: [],
        displayTags: [],
    });

    let previousLogicalDetailsOpen = false;
    let previousLogicalModelKey: string | null = null;
    let schemaTriggerInitialized = false;
    let schemaLoadedFor: string | null = null;

    function loadEditableSchema() {
        if (!activeModelId || !modelDetails || $viewMode !== "logical" || isCollapsed) {
            return;
        }

        const schemaKey = `${activeModelId}:${modelDetails.version ?? ""}`;
        if (schemaLoadedFor === schemaKey) {
            return;
        }
        schemaLoadedFor = schemaKey;

        schemaManager ??= new SchemaManager((newState) => {
            schemaState = newState;
        });
        void schemaManager
            .loadSchema(
                modelDetails.name,
                modelDetails.version,
                modelDetails.tags,
                modelDetails.columns,
            )
            .catch(() => {
                // SchemaManager records the error and keeps manifest columns as fallback.
            });
    }

    // Defer editable schema work until logical details are opened.
    $effect(() => {
        const logicalDetailsOpen = $viewMode === "logical" && !isCollapsed;
        const logicalModelKey = activeModelId
            ? `${activeModelId}:${modelDetails?.version ?? ""}`
            : null;
        const openedLogicalDetails =
            schemaTriggerInitialized &&
            logicalDetailsOpen &&
            (!previousLogicalDetailsOpen || previousLogicalModelKey !== logicalModelKey);

        if (openedLogicalDetails) {
            loadEditableSchema();
        }

        schemaTriggerInitialized = true;
        previousLogicalDetailsOpen = logicalDetailsOpen;
        previousLogicalModelKey = logicalModelKey;
    });

    // Expose active model info on node data (ephemeral; not persisted)
    $effect(() => {
        updateNodeData(id, {
            _activeModelId: activeModelId || null,
            _activeModelName: modelDetails?.name || null,
            _activeModelVersion:
                modelDetails?.version === undefined
                    ? null
                    : (modelDetails?.version as number | null),
        });
    });

    // Preserve edge selection when switching models (defensive measure)
    let previousModelIndex = $state(0);
    let lastKnownSelectedEdges = $state<Set<string>>(new Set());

    // Continuously track selected edges
    $effect(() => {
        const selectedIds = new Set($edges.filter(e => e.selected).map(e => e.id));
        if (selectedIds.size > 0) {
            lastKnownSelectedEdges = selectedIds;
        }
    });

    // Restore selection when model index changes
    $effect(() => {
        const currentModelIndex = activeModelIndex;
        if (previousModelIndex !== currentModelIndex && allBoundModels.length > 1 && lastKnownSelectedEdges.size > 0) {
            // Model switch occurred - restore previously selected edges after a microtask
            queueMicrotask(() => {
                $edges = $edges.map(edge => ({
                    ...edge,
                    selected: lastKnownSelectedEdges.has(edge.id)
                }));
            });
        }
        previousModelIndex = currentModelIndex;
    });

    function addAdditionalModel(modelId: string) {
        const current = (data.additional_models as string[]) || [];
        if (!current.includes(modelId)) {
            updateNodeData(id, { additional_models: [...current, modelId] });
        }
    }

    function removeAdditionalModel(index: number) {
        const current = (data.additional_models as string[]) || [];
        const newModels = current.filter((_, i) => i !== index);
        updateNodeData(id, { additional_models: newModels.length > 0 ? newModels : undefined });
        // Reset to primary if we removed the active model
        if (activeModelIndex > 0 && activeModelIndex === index + 1) {
            activeModelIndex = 0;
        } else if (activeModelIndex > index + 1) {
            activeModelIndex--;
        }
    }

    function updateLabel(e: Event) {
        const label = (e.target as HTMLInputElement).value.trim();
        // Just update the label without changing ID (for real-time typing)
        // Labels can contain spaces - only the ID (generated on blur) converts spaces to underscores
        updateNodeData(id, { label });
    }

    let labelBeforeEdit: string | null = null;

    function handleLabelFocus() {
        labelBeforeEdit = (data.label || "").trim();
    }

    function updateIdFromLabel(e: Event) {
        // Called on blur - update the ID based on final label
        // Convert label to title-case before updating
        const rawLabel = (e.target as HTMLInputElement).value.trim();
        if (labelBeforeEdit !== null && rawLabel === labelBeforeEdit) {
            // Reset so future edits can be detected
            labelBeforeEdit = null;
            return;
        }
        const label = toTitleCase(rawLabel);
        const newId = generateSlug(label, $nodes.map((n) => n.id), id);

        // If ID changes, update the node and all relationships (edge IDs stay stable)
        if (newId !== id) {
            $edges = renameNodeInEdges($edges, id, newId);
            $nodes = renameNode($nodes, id, newId, { label });
        }
    }

    function updateDescription(e: Event) {
        const description = (e.target as HTMLTextAreaElement).value;
        updateNodeData(id, { description });
    }

    let isDragOver = $state(false);

    async function onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation(); // Stop bubbling to canvas
        event.stopImmediatePropagation();
        isDragOver = false;

        const json = event.dataTransfer?.getData("application/model-ref");
        if (!json) return;
        const model: ModelInfo = JSON.parse(json);

        // Track the final ID (may change during auto-naming)
        let finalId = id;
        
        // If primary model exists, add as additional model; otherwise set as primary
        let newlyAddedModelId: string | null = null;
        if (boundModelName) {
            addAdditionalModel(model.unique_id);
            newlyAddedModelId = model.unique_id;
            // Switch to the newly added model (will be at index = current additional_models.length + 1)
            const currentAdditional = (data.additional_models as string[]) || [];
            activeModelIndex = currentAdditional.length + 1;
        } else {
            // Store the full unique_id (e.g. "model.elmo.entity_booking")
            const updates: Record<string, unknown> = { model_ref: model.unique_id };
            const hasDescription = (data.description || "").trim().length > 0;
            if (!hasDescription && (model.description || "").trim().length > 0) {
                updates.description = model.description;
            }
            const inferredType = classifyModelTypeFromPrefixes(
                model.name,
                $dimensionPrefixes,
                $factPrefixes
            );
            if (inferredType) {
                updates.entity_type = inferredType;
            }
            
            // Auto-naming: Check if entity is unnamed and binding primary model
            const isUnnamed = id.startsWith('new_entity') && data.label === 'New Entity';
            
            if (isUnnamed) {
                try {
                    // Extract model name from unique_id
                    const modelName = extractModelNameFromUniqueId(model.unique_id);
                    // Format label (title-case with spaces), stripping entity prefixes
                    const formattedLabel = formatModelNameForLabel(modelName, $labelPrefixes);
                    // Generate new ID using generateSlug
                    const newId = generateSlug(formattedLabel, $nodes.map(n => n.id), id);
                    
                    // If ID changes, update edges and node
                    if (newId !== id) {
                        $edges = renameNodeInEdges($edges, id, newId);
                        // Include ALL updates (model_ref, description, label) on the renamed node
                        $nodes = renameNode($nodes, id, newId, {
                            label: formattedLabel,
                            ...updates,
                        });
                        
                        // Use new ID for updateNodeData call
                        finalId = newId;
                        updates.label = formattedLabel;
                    } else {
                        // ID didn't change, just update label
                        updates.label = formattedLabel;
                    }
                } catch (e) {
                    // If model name extraction fails, silently skip auto-naming (graceful degradation)
                    console.warn("Failed to auto-name entity from model:", e);
                }
            }
            
            updateNodeData(finalId, updates);
        }

        // Auto-create relationships from yml relationship tests
        try {
            const inferred = await inferRelationships();

            // Current node: include the model we just bound (data model hasn't saved yet)
            let currentNodeModels: string[];
            if (boundModelName) {
                const currentAdditional = (data.additional_models as string[]) || [];
                currentNodeModels = [boundModelName, ...currentAdditional];
                if (newlyAddedModelId) {
                    currentNodeModels.push(newlyAddedModelId);
                }
            } else {
                currentNodeModels = [model.unique_id];
            }
            const modelToEntity = buildModelToEntityMap($nodes, id, finalId, currentNodeModels);

            const relationships = remapInferredRelationships(
                inferred,
                modelToEntity,
                finalId,
                $nodes.map((n) => n.id),
            );
            for (const remappedRel of relationships) {
                // Merge relationship into edges (will aggregate by entity pair)
                $edges = mergeRelationshipIntoEdges($edges, remappedRel);
            }
        } catch (e) {
            console.warn("Could not infer relationships:", e);
        }
    }

    function onDragOver(event: DragEvent) {
        event.preventDefault(); // Essential to allow drop
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "copy";
        }
    }

    function onDragEnter(event: DragEvent) {
        event.preventDefault();
        isDragOver = true;
    }

    function onDragLeave(event: DragEvent) {
        isDragOver = false;
    }


    function startDimensionResize(
        event: PointerEvent,
        type: ResizeDimension,
    ) {
        event.stopPropagation();
        event.preventDefault();

        const startX = event.clientX;
        const startY = event.clientY;
        const initialWidth = nodeWidth;
        const initialHeight = columnPanelHeight;

        function onMove(moveEvent: PointerEvent) {
            if (type === "width") {
                updateNodeData(id, computeResizePatch(type, initialWidth, moveEvent.clientX - startX));
            } else {
                updateNodeData(id, computeResizePatch(type, initialHeight, moveEvent.clientY - startY));
            }
        }

        function onUp() {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
        }

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    }

    function unbind() {
        updateNodeData(id, { model_ref: null });

        // Clear field mappings on edges connected to this entity
        edges.update((list) =>
            list.map((edge) => {
                if (edge.source === id || edge.target === id) {
                    // Create new data object without source_field and target_field
                    const { source_field, target_field, ...restData } =
                        (edge.data || {}) as Record<string, unknown>;
                    return {
                        ...edge,
                        data: restData,
                    };
                }
                return edge;
            }),
        );
    }

    function toggleCollapse() {
        updateNodeData(id, { collapsed: !isCollapsed });
    }

    function deleteEntity() {
        try {
            // Remove all edges that reference this node
            edges.update((list) =>
                list.filter((edge) => edge.source !== id && edge.target !== id),
            );

            // Remove the node itself
            nodes.update((list) => list.filter((node) => node.id !== id));

            closeDeleteConfirmModal();
        } catch (error) {
            console.error("Failed to delete entity:", error);
            alert("Failed to delete entity. Please try again.");
            closeDeleteConfirmModal();
        }
    }

    function setEntityType(newType: "fact" | "dimension" | "unclassified") {
        updateNodeData(id, { entity_type: newType });
    }

    // Tag editing functionality
    // For bound entities, the editor displays the union of the dbt-mirrored
    // `dbt_tags` and the Trellis-authored `ui_tags`. Unbound entities have no
    // schema.yml to mirror, so `tags` remains the single freely-editable field.
    let entityTags = $derived(
        isBound
            ? normalizeTags([...readFrameworkTags(data), ...((data.ui_tags || []) as string[])])
            : normalizeTags(data.tags),
    );

    // dbt_tags are always dbt-owned: they render read-only in the tag editor
    // (no remove affordance) because a Trellis push never removes a tag it
    // doesn't own. Only meaningful for bound entities.
    let readOnlyTags = $derived(isBound ? normalizeTags(readFrameworkTags(data)) : []);

    // Roles display (for dimensions): role strings, deduplicated case-insensitively
    let entityRoles = $derived(uniqueRoleNames(data.roles));

    function handleTagsUpdate(newTags: string[]) {
        const allSelectedIds = isBatchEditing ? [id, ...selectedEntityNodes.map((n) => n.id)] : [id];

        allSelectedIds.forEach((nodeId) => {
            const node = $nodes.find((n): n is EntityFlowNode => isEntityNode(n) && n.id === nodeId);
            const nodeIsBound = !!readModelRef(node?.data ?? {});

            if (nodeIsBound) {
                // `dbt_tags` is a dbt-mirrored, reconcile-owned field for bound
                // entities (schema.yml is authoritative) — never hand-written here.
                // An edit in the tag editor only ever changes `ui_tags`; a
                // dbt-mirrored tag missing from `newTags` (e.g. the user tried to
                // remove a read-only chip) is not treated as a removal, since dbt wins.
                const uiTags = computeUiTagsAfterEdit(readFrameworkTags(node?.data ?? {}), newTags);
                updateNodeData(nodeId, { ui_tags: uiTags });
            } else {
                // Unbound entities have no schema.yml to mirror; `tags` is the
                // single freely-editable field.
                updateNodeData(nodeId, { tags: newTags });
            }
        });
    }

    // Source system update handler (only for unbound entities)
    function handleSourcesUpdate(newSources: string[]) {
        // Source systems are only editable for unbound entities
        if (isBound) {
            console.warn('Source systems for bound entities are derived from lineage and cannot be edited');
            return;
        }

        updateNodeData(id, {
            source_system: newSources
        });
    }

    // Field drafting functionality
    let draftedFields = $derived((data.drafted_fields || []) as DraftedField[]);

    function setDraftedFields(updatedFields: DraftedField[]) {
        updateNodeData(id, { drafted_fields: updatedFields });
    }
</script>

<div
    class="rounded-lg border bg-white shadow-sm hover:shadow-md relative transition-all duration-200"
    class:border-primary-500={isBound && !selected}
    class:border-gray-300={!isBound && !selected && !isDragOver}
    class:ring-2={selected || isDragOver}
    class:ring-primary-500={selected}
    class:ring-opacity-50={selected}
    class:border-primary-600={selected}
    class:ring-primary-200={isDragOver && !selected}
    class:border-primary-400={isDragOver && !selected}
    style={`width:${nodeWidth}px`}
    ondrop={onDrop}
    ondragover={onDragOver}
    ondragenter={onDragEnter}
    ondragleave={onDragLeave}
    role="presentation"
>
    <!-- Handles on all 4 sides for flexible edge routing -->
    <!-- Top -->
    <Handle type="target" position={Position.Top} id="top-target" class="connection-handle !w-5 !h-5 !rounded-full !bg-transparent !border-0" title="Drag to other entity to create relationship">
        <Icon icon="mdi:arrow-up" class="w-3 h-3 pointer-events-none" />
    </Handle>
    <Handle type="source" position={Position.Top} id="top-source" class="connection-handle !w-5 !h-5 !rounded-full !bg-transparent !border-0" title="Drag to other entity to create relationship">
        <Icon icon="mdi:arrow-up" class="w-3 h-3 pointer-events-none" />
    </Handle>

    <!-- Bottom -->
    <Handle type="target" position={Position.Bottom} id="bottom-target" class="connection-handle !w-5 !h-5 !rounded-full !bg-transparent !border-0" title="Drag to other entity to create relationship">
        <Icon icon="mdi:arrow-down" class="w-3 h-3 pointer-events-none" />
    </Handle>
    <Handle type="source" position={Position.Bottom} id="bottom-source" class="connection-handle !w-5 !h-5 !rounded-full !bg-transparent !border-0" title="Drag to other entity to create relationship">
        <Icon icon="mdi:arrow-down" class="w-3 h-3 pointer-events-none" />
    </Handle>

    <EntityNodeHeader
        {id}
        {data}
        {isCollapsed}
        {isBound}
        {boundModelName}
        {isDimensionalModeling}
        {lineageEnabled}
        {exposuresEnabled}
        {hasExposuresData}
        unboundHint={frameworkCopy.unboundHint}
        onToggleCollapse={toggleCollapse}
        onLabelFocus={handleLabelFocus}
        onLabelInput={updateLabel}
        onLabelBlur={updateIdFromLabel}
        onSetEntityType={setEntityType}
    />

    <!-- Body -->
    {#if !isCollapsed}
        <div class="p-2.5 nodrag">
            {#if $viewMode === "logical" && isBound && modelDetails}
                <div class="text-xs">
                    <div
                        class="font-mono text-gray-500 mb-2.5 bg-gray-50 p-1.5 rounded border border-gray-100 break-all text-[11px]"
                    >
                        {modelDetails.schema}.{modelDetails.table}
                    </div>
                    {#if modelDetails.materialization}
                        <div
                            class="mb-2.5 text-gray-500 flex items-center gap-2"
                        >
                            <span
                                class="font-medium text-[10px] uppercase tracking-wider"
                                >Materialization</span
                            >
                            <span
                                class="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-[10px] font-semibold uppercase border border-gray-200"
                            >
                                {modelDetails.materialization}
                            </span>
                        </div>
                    {/if}

                    <!-- Source Systems (Logical View Only) - Bound entities: read-only badges from lineage -->
                    {#if $viewMode === "logical" && isBound}
                        <div class="mb-2.5 text-gray-500 flex flex-wrap items-center gap-2">
                            <span
                                class="font-medium text-[10px] uppercase tracking-wider"
                                >Source Systems</span
                            >
                            {#if data.source_system && data.source_system.length > 0}
                                <div class="flex flex-wrap gap-1.5">
                                    {#each data.source_system as sourceSystem}
                                        <span
                                            class:source-chip={true}
                                            style={getSourceChipStyle(sourceSystem, $sourceColors)}
                                        >
                                            {sourceSystem}
                                        </span>
                                    {/each}
                                </div>
                            {:else}
                                <span class="text-[10px] text-gray-400 italic">
                                    No source systems in lineage
                                </span>
                            {/if}
                        </div>
                    {/if}

                    <!-- Model Tabs (when multiple models are bound) -->
                    {#if allBoundModels.length > 1}
                        <div class="mb-2.5 flex items-center gap-1 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
                            {#each allBoundModels as modelId, index}
                                {@const isActive = activeModelIndex === index}
                                {@const isPrimary = index === 0}
                                {@const modelName = getModelShortName(modelId)}
                                <div
                                    class="group relative flex items-center"
                                >
                                    <button
                                        onclick={(e) => {
                                            e.stopPropagation();
                                            activeModelIndex = index;
                                        }}
                                        class="px-2 py-1 text-[10px] rounded border transition-colors whitespace-nowrap flex items-center gap-1"
                                        class:bg-primary-500={isActive}
                                        class:text-white={isActive}
                                        class:border-primary-500={isActive}
                                        class:bg-white={!isActive}
                                        class:text-gray-600={!isActive}
                                        class:border-gray-300={!isActive}
                                        class:hover:bg-gray-50={!isActive}
                                        title={modelId}
                                    >
                                        {modelName}
                                        {#if isPrimary}
                                            <span class="text-[8px] opacity-70" title="Primary model">●</span>
                                        {/if}
                                    </button>
                                    {#if !isPrimary}
                                        <button
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                removeAdditionalModel(index - 1);
                                            }}
                                            class="absolute -right-1 -top-1 opacity-0 group-hover:opacity-100 hover:text-danger-500 transition-opacity bg-white rounded-full border border-gray-200 p-0.5"
                                            title="Remove model"
                                        >
                                            <Icon icon="lucide:x" class="w-2 h-2" />
                                        </button>
                                    {/if}
                                </div>
                            {/each}
                            <!-- Add model button -->
                            <button
                                class="px-2 py-1 text-[10px] rounded border border-dashed border-gray-300 text-gray-500 hover:border-primary-500 hover:text-primary-500 transition-colors flex items-center gap-1 flex-shrink-0"
                                title={frameworkCopy.addModelTooltip}
                            >
                                <Icon icon="lucide:plus" class="w-3 h-3" />
                            </button>
                        </div>
                    {/if}

                    <EntityNodeTags
                        wrapperClass="mb-2.5"
                        tags={entityTags}
                        readOnlyTags={readOnlyTags}
                        isBatchEditing={isBatchEditing}
                        batchCount={selectedEntityNodes.length + 1}
                        onUpdate={handleTagsUpdate}
                    />
                    
                    {#if entityRoles && entityRoles.length > 0}
                        <EntityNodeRoles wrapperClass="mb-2.5" roles={entityRoles} />
                    {/if}

                    <EntityNodeFields
                        {id}
                        nodeLabel={data.label || id}
                        columns={modelDetails?.columns}
                        {draftedFields}
                        {columnPanelHeight}
                        {frameworkCopy}
                        modelName={modelDetails?.name}
                        onDraftedFieldsChange={setDraftedFields}
                    />

                    {#if schemaState.error}
                        <div
                            class="mt-2 p-2 bg-danger-50 border border-danger-200 rounded text-danger-800 text-[10px]"
                        >
                            {schemaState.error}
                        </div>
                    {/if}

                    <div class="flex gap-2 mt-2">
                        <button
                            class="flex-1 text-[10px] text-danger-500 hover:bg-danger-50 p-1.5 rounded border border-danger-100 transition-colors font-medium"
                            onclick={unbind}
                        >
                            Unbind
                        </button>
                    </div>
                </div>
            {:else}
                <!-- When not bound to dbt model: show conceptual view OR field editor based on view mode -->
                {#if $viewMode === "logical"}
                    <!-- Logical View - Field Editor -->
                    <div class="text-xs">
                        <div
                            class="mb-2 p-2 bg-amber-50 border border-amber-100 rounded text-amber-800 text-[10px] flex items-center gap-2"
                        >
                            <Icon
                                icon="lucide:alert-triangle"
                                class="w-3 h-3"
                            />
                            Generic datatypes (draft mode)
                        </div>

                        <EntityNodeTags
                            wrapperClass="mb-2.5"
                            tags={entityTags}
                            isBatchEditing={isBatchEditing}
                            batchCount={selectedEntityNodes.length + 1}
                            onUpdate={handleTagsUpdate}
                        />
                        
                        {#if entityRoles && entityRoles.length > 0}
                            <EntityNodeRoles wrapperClass="mb-2.5" roles={entityRoles} />
                        {/if}

                        <!-- Source Systems Editor for Unbound Entities (Logical View Only) -->
                        {#if $viewMode === "logical" && !isBound}
                            <div class="mb-2.5">
                                {#if isBatchEditing}
                                    <BatchEditBanner count={selectedEntityNodes.length + 1} />
                                {/if}
                                <div class="flex items-center gap-2 flex-wrap mb-1">
                                    <span
                                        class="font-medium text-[10px] uppercase tracking-wider text-gray-500"
                                    >Source Systems</span
                                    >
                                    <div class="flex flex-wrap gap-1.5">
                                        {#each (data.source_system || []) as sourceSystem}
                                            <span
                                                class:source-chip={true}
                                                style={getSourceChipStyle(sourceSystem, $sourceColors)}
                                            >
                                                {sourceSystem}
                                            </span>
                                        {/each}
                                        <button
                                            onmousedown={(e) => e.preventDefault()}
                                            onclick={() => openSourceEditorModal(data.label || "Entity", id, (data.source_system || []))}
                                            class="px-1.5 py-0.5 bg-blue-50 text-blue-500 rounded text-[10px] font-semibold border border-blue-200 hover:bg-blue-100 focus:outline-none focus:ring-1 focus:ring-blue-400"
                                            title="Edit source systems"
                                            aria-label="Edit source systems"
                                        >
                                            <Icon icon="lucide:plus" class="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        {/if}

                        <EntityNodeFields
                            {id}
                            nodeLabel={data.label || id}
                            columns={modelDetails?.columns}
                            {draftedFields}
                            {columnPanelHeight}
                            {frameworkCopy}
                            modelName={modelDetails?.name}
                            onDraftedFieldsChange={setDraftedFields}
                        />
                    </div>
                {:else}
                    <!-- Conceptual View -->
                    <textarea
                        value={data.description || ""}
                        oninput={updateDescription}
                        class="w-full text-xs text-gray-600 resize-y min-h-[60px] bg-gray-50 focus:outline-none focus:bg-white focus:ring-1 focus:ring-primary-500 rounded p-1.5 border border-gray-200"
                        placeholder="Description..."
                    ></textarea>

                    <EntityNodeTags
                        wrapperClass="mt-2.5"
                        tags={entityTags}
                        readOnlyTags={readOnlyTags}
                        isBatchEditing={isBatchEditing}
                        batchCount={selectedEntityNodes.length + 1}
                        onUpdate={handleTagsUpdate}
                    />
                    
                    {#if entityRoles && entityRoles.length > 0}
                        <EntityNodeRoles wrapperClass="mt-2.5" roles={entityRoles} />
                    {/if}
                    {#if isBound}
                        <div class="mt-2 space-y-1.5">
                            <div
                                class="text-xs text-primary-600 flex items-center justify-between bg-primary-50 p-1.5 rounded border border-primary-100"
                            >
                                <span
                                    class="truncate font-medium flex items-center gap-1"
                                    title={boundModelName}
                                >
                                    <Icon icon="lucide:link" class="w-3 h-3" />
                                    {boundModelName}</span
                                >
                                <button
                                    onclick={unbind}
                                    class="text-primary-600 hover:text-danger-500 ml-1 px-1 transition-colors"
                                >
                                    <Icon icon="lucide:x" class="w-3 h-3" />
                                </button>
                            </div>
                            {#if additionalModels.length > 0}
                                <div class="text-[10px] text-gray-500 flex items-center gap-1 flex-wrap">
                                    <span class="uppercase tracking-wide">Also bound:</span>
                                    {#each additionalModels as modelId}
                                        <span
                                            class="px-1.5 py-0.5 rounded border border-gray-200 bg-white text-gray-600 flex items-center gap-1"
                                            title={modelId}
                                        >
                                            <Icon icon="lucide:layers" class="w-3 h-3 text-gray-400" />
                                            {getModelShortName(modelId)}
                                        </span>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    {:else}
                        <div
                            class="mt-2 text-[10px] text-gray-400 text-center border border-dashed border-gray-300 rounded p-3 bg-gray-50 pointer-events-none"
                        >
                            {frameworkCopy.emptyBindingHint}
                        </div>
                    {/if}
                {/if}
            {/if}
        </div>
    {/if}


    <div
        class="width-resize-handle nodrag nopan"
        onpointerdown={(event) => startDimensionResize(event, "width")}
        title="Drag to resize width"
    ></div>

    {#if $viewMode === "logical"}
        <div
            class="height-resize-handle nodrag nopan"
            onpointerdown={(event) => startDimensionResize(event, "height")}
            title="Drag to show more columns"
        ></div>
    {/if}
</div>

<style>
    .width-resize-handle {
        position: absolute;
        top: 0;
        right: -3px;
        width: 6px;
        height: 100%;
        cursor: ew-resize;
        border-radius: 999px;
    }

    .width-resize-handle:hover,
    .height-resize-handle:hover {
        background: rgba(38, 166, 154, 0.2);
    }

    :global(.connection-handle) {
        color: transparent;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: color 0.15s, background-color 0.15s;
    }

    :global(.connection-handle:hover) {
        color: rgb(38 166 154) !important; /* teal #26A69A */
        background-color: rgb(224 242 241) !important; /* teal-50 */
    }

    .height-resize-handle {
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 100%;
        height: 6px;
        cursor: ns-resize;
        border-radius: 999px;
    }

    .source-chip {
        display: inline-flex;
        align-items: center;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
