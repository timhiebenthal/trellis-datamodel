<script lang="ts">
    import {
        Handle,
        Position,
        useSvelteFlow,
        type NodeProps,
    } from "@xyflow/svelte";
    import {
        viewMode,
        dbtModels,
        nodes,
        edges,
        draggingField,
        exposureEntityFilter,
    } from "$lib/stores";
    import type { DbtModel, DraftedField, ModelSchemaColumn, EntityData } from "$lib/types";
    import {
        inferRelationships,
        getModelSchema,
        updateModelSchema,
        getLineage,
    } from "$lib/api";
    import {
        getParallelOffset,
        generateSlug,
        normalizeTags,
        mergeRelationshipIntoEdges,
        detectFieldSemantics,
        formatModelNameForLabel,
        extractModelNameFromUniqueId,
        toTitleCase,
    } from "$lib/utils";
    import { getContext } from "svelte";
import DeleteConfirmModal from "./DeleteConfirmModal.svelte";
import UndescribedAttributesWarningModal from "./UndescribedAttributesWarningModal.svelte";
    import { openLineageModal } from "$lib/stores";
import Icon from "@iconify/svelte";
    import { readable, type Readable } from "svelte/store";

    function openExposuresView(event: MouseEvent) {
        event.stopPropagation(); // Prevent collapse toggle
        exposureEntityFilter.set(id);
        viewMode.set('exposures');
    }

    let { data: rawData, id, selected }: NodeProps = $props();
    // Cast data to EntityData for proper typing - use $derived to maintain reactivity
    let data = $derived(rawData as unknown as EntityData);

    const { updateNodeData, getNodes } = useSvelteFlow();
    let showDeleteModal = $state(false);
    let showEntityTypeMenu = $state(false);
    let showUndescribedAttributesWarning = $state(false);
    let undescribedAttributeNames = $state<string[]>([]);
    let warningResolve: ((value: boolean) => void) | null = null;
    // Lineage modal is rendered at page-level (outside SvelteFlow) via a global store

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

    // Reactive binding check
    let boundModelName = $derived(data.dbt_model as string | undefined);
    let additionalModels = $derived((data.additional_models as string[]) || []);
    let allBoundModels = $derived(
        boundModelName ? [boundModelName, ...additionalModels] : []
    );
    let activeModelIndex = $state(0); // ephemeral, defaults to primary
    let activeModelId = $derived(allBoundModels[activeModelIndex] || boundModelName);
    let isBound = $derived(!!boundModelName);
    let isCollapsed = $derived(data.collapsed ?? false);
    const DEFAULT_WIDTH = 320;
    const DEFAULT_PANEL_HEIGHT = 200;
    const MIN_WIDTH = 280;
    const MAX_WIDTH = 600;
    const MIN_PANEL_HEIGHT = 120;
    const MAX_PANEL_HEIGHT = 600;
    let nodeWidth = $derived(data.width ?? DEFAULT_WIDTH);
    let columnPanelHeight = $derived(data.panelHeight ?? DEFAULT_PANEL_HEIGHT);

    // Find model details by unique_id (e.g. "model.elmo.entity_booking")
    let modelDetails = $derived(
        activeModelId ? $dbtModels.find((m) => m.unique_id === activeModelId) : null,
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

    // Schema editing state for bound models
    let editableColumns = $state<ModelSchemaColumn[]>([]);
    let schemaLoading = $state(false);
    let schemaSaving = $state(false);
    let schemaError = $state<string | null>(null);
    let hasUnsavedChanges = $state(false);

    // Fetch schema when active model changes
    $effect(() => {
        if (activeModelId && modelDetails) {
            loadSchema();
        } else {
            editableColumns = [];
            hasUnsavedChanges = false;
        }
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

    async function loadSchema() {
        if (!modelDetails) return;

        schemaLoading = true;
        schemaError = null;

        try {
            const schema = await getModelSchema(
                modelDetails.name,
                modelDetails.version ?? undefined,
            );
            const hasSchemaColumns =
                Array.isArray(schema?.columns) && schema.columns.length > 0;

            if (hasSchemaColumns) {
                // Use columns from schema (includes descriptions)
                editableColumns = schema.columns.map(
                    (col: ModelSchemaColumn) => ({
                        name: col.name,
                        data_type: col.data_type || "text",
                        description: col.description || "",
                    }),
                );
            } else {
                // Fallback to manifest columns if schema not found
                editableColumns = modelDetails.columns.map((col) => ({
                    name: col.name,
                    data_type: col.type || "text",
                    description: "",
                }));
            }

            // Only sync tags from dbt schema for the primary model
            if (activeModelIndex === 0) {
                // Track tag sources separately to prevent inherited tag propagation
                const schemaTags = normalizeTags(schema?.tags);
                const manifestTags = normalizeTags(modelDetails.tags);
                
                // Combine for display: schema tags (explicit) + manifest tags (may include inherited)
                // But track them separately so we only save schema tags
                const displayTags = [...new Set([...schemaTags, ...manifestTags])];

                updateNodeData(id, { 
                    tags: displayTags,
                    _schemaTags: schemaTags,
                    _manifestTags: manifestTags
                });
            }

            hasUnsavedChanges = false;
        } catch (e) {
            console.error("Error loading schema:", e);
            schemaError = "Failed to load schema";
            // Fallback to manifest columns
            editableColumns = modelDetails.columns.map((col) => ({
                name: col.name,
                data_type: col.type || "text",
                description: "",
            }));
        } finally {
            schemaLoading = false;
        }
    }

    // Show warning modal and wait for user decision
    function showUndescribedAttributesWarningModal(attributeNames: string[]): Promise<boolean> {
        return new Promise((resolve) => {
            undescribedAttributeNames = attributeNames;
            warningResolve = resolve;
            showUndescribedAttributesWarning = true;
        });
    }

    function handleWarningConfirm() {
        showUndescribedAttributesWarning = false;
        if (warningResolve) {
            warningResolve(true);
            warningResolve = null;
        }
    }

    function handleWarningCancel() {
        showUndescribedAttributesWarning = false;
        if (warningResolve) {
            warningResolve(false);
            warningResolve = null;
        }
    }

    async function saveSchema() {
        if (!modelDetails) return;

        // Check for attributes without descriptions
        const undescribedAttributes = editableColumns
            .filter((col) => col.name && (!col.description || col.description.trim().length === 0))
            .map((col) => col.name);

        if (undescribedAttributes.length > 0) {
            const proceed = await showUndescribedAttributesWarningModal(undescribedAttributes);
            if (!proceed) {
                return;
            }
        }

        schemaSaving = true;
        schemaError = null;

        try {
            // Only save schema tags (explicit), not manifest tags (which may be inherited)
            // User-added tags are added to _schemaTags when addTag is called
            const tagsToSave = normalizeTags(data._schemaTags);
            
            await updateModelSchema(
                modelDetails.name,
                editableColumns.map((col) => ({
                    name: col.name,
                    data_type: col.data_type,
                    description: col.description,
                })),
                data.description,
                tagsToSave,
                modelDetails.version ?? undefined,
            );
            hasUnsavedChanges = false;
        } catch (e: any) {
            console.error("Error saving schema:", e);
            schemaError = e.message || "Failed to save schema";
        } finally {
            schemaSaving = false;
        }
    }

    function updateEditableColumn(
        index: number,
        updates: Partial<ModelSchemaColumn>,
    ) {
        editableColumns = editableColumns.map((col, i) =>
            i === index ? { ...col, ...updates } : col,
        );
        hasUnsavedChanges = true;
    }

    function addEditableColumn() {
        editableColumns = [
            ...editableColumns,
            {
                name: "",
                data_type: "text",
                description: "",
            },
        ];
        hasUnsavedChanges = true;
    }

    function deleteEditableColumn(index: number) {
        editableColumns = editableColumns.filter((_, i) => i !== index);
        hasUnsavedChanges = true;
    }

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

    function getModelShortName(modelId: string): string {
        return modelId.includes(".") ? modelId.split(".").pop()! : modelId;
    }

    function updateLabel(e: Event) {
        const label = (e.target as HTMLInputElement).value.trim();
        // Just update the label without changing ID (for real-time typing)
        // Labels can contain spaces - only the ID (generated on blur) converts spaces to underscores
        updateNodeData(id, { label });
    }

    function updateIdFromLabel(e: Event) {
        // Called on blur - update the ID based on final label
        // Convert label to title-case before updating
        const rawLabel = (e.target as HTMLInputElement).value.trim();
        const label = toTitleCase(rawLabel);
        const newId = generateSlug(label, $nodes.map((n) => n.id), id);

        // If ID changes, update the node and all relationships
        if (newId !== id) {
            // Update all edges that reference this node
            $edges = $edges.map((edge) => {
                let updatedEdge = { ...edge };
                if (edge.source === id) {
                    updatedEdge.source = newId;
                }
                if (edge.target === id) {
                    updatedEdge.target = newId;
                }
                // Update edge ID if it was based on source-target pattern
                // FIXED: Do NOT update edge ID. Changing IDs causes duplicates on reload because
                // the backend saves the new ID, but might also keep the old one if not handled perfectly,
                // or more likely, the "baseId" logic in Canvas/Page creates collisions.
                // Keeping the ID stable is safer.
                return updatedEdge;
            });

            // Update the node itself with new ID
            $nodes = $nodes.map((node) => {
                if (node.id === id) {
                    return {
                        ...node,
                        id: newId,
                        data: { ...node.data, label },
                    };
                }
                return node;
            });
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

        const json = event.dataTransfer?.getData("application/dbt-model");
        if (!json) return;
        const model: DbtModel = JSON.parse(json);

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
            const updates: Record<string, unknown> = { dbt_model: model.unique_id };
            const hasDescription = (data.description || "").trim().length > 0;
            if (!hasDescription && (model.description || "").trim().length > 0) {
                updates.description = model.description;
            }
            
            // Auto-naming: Check if entity is unnamed and binding primary model
            const isUnnamed = id.startsWith('new_entity') && data.label === 'New Entity';
            let finalId = id; // Track the final ID to use for updateNodeData
            
            if (isUnnamed) {
                try {
                    // Extract model name from unique_id
                    const modelName = extractModelNameFromUniqueId(model.unique_id);
                    // Format label (title-case with spaces)
                    const formattedLabel = formatModelNameForLabel(modelName);
                    // Generate new ID using generateSlug
                    const newId = generateSlug(formattedLabel, $nodes.map(n => n.id), id);
                    
                    // If ID changes, update edges and node
                    if (newId !== id) {
                        // Update all edges that reference this node
                        $edges = $edges.map((edge) => {
                            let updatedEdge = { ...edge };
                            if (edge.source === id) {
                                updatedEdge.source = newId;
                            }
                            if (edge.target === id) {
                                updatedEdge.target = newId;
                            }
                            // Do NOT update edge ID (see comment at line 310-313)
                            return updatedEdge;
                        });
                        
                        // Update the node itself with new ID - include ALL updates (dbt_model, description, label)
                        $nodes = $nodes.map((node) => {
                            if (node.id === id) {
                                const updatedData = { 
                                    ...node.data, 
                                    label: formattedLabel,
                                    ...updates // Include dbt_model and description from updates
                                };
                                return {
                                    ...node,
                                    id: newId,
                                    data: updatedData,
                                };
                            }
                            return node;
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
            const inferred = await inferRelationships({ includeUnbound: true });

                // Build model name -> entity ID map from current canvas state
                // Include the model we just bound (since data model hasn't saved yet)
                const modelToEntity: Record<string, string> = {};
                for (const node of $nodes) {
                    let boundModels: string[] = [];
                    if (node.id === id) {
                        // Current node: include the model we just added
                        if (boundModelName) {
                            const currentAdditional = (data.additional_models as string[]) || [];
                            boundModels = [boundModelName, ...currentAdditional];
                            if (newlyAddedModelId) {
                                boundModels.push(newlyAddedModelId);
                            }
                        } else {
                            boundModels = [model.unique_id];
                        }
                    } else {
                        // Other nodes: get all bound models
                        const primary = node.data?.dbt_model as string | undefined;
                        const additional = (node.data?.additional_models as string[]) || [];
                        if (primary) {
                            boundModels = [primary, ...additional];
                        }
                    }
                    
                    for (const boundModel of boundModels) {
                        if (boundModel && typeof boundModel === "string") {
                            // Extract model name from unique_id, handling versioned models:
                            // "model.project.name" -> maps "name"
                            // "model.project.name.v1" -> maps "name" (base name used by backend)
                            const parts = boundModel.split(".");
                            if (parts.length >= 3 && parts[0] === "model") {
                                const lastPart = parts[parts.length - 1];
                                const isVersioned = /^v\d+$/.test(lastPart);
                                
                                if (isVersioned && parts.length >= 4) {
                                    // Versioned model: map base name (backend returns base_model_name)
                                    const baseName = parts[parts.length - 2];
                                    modelToEntity[baseName] = node.id;
                                } else {
                                    modelToEntity[lastPart] = node.id;
                                }
                            } else {
                                const modelName = boundModel.includes(".")
                                    ? boundModel.split(".").pop()!
                                    : boundModel;
                                modelToEntity[modelName] = node.id;
                            }
                        }
                    }
                    // Also map entity ID to itself
                    modelToEntity[node.id] = node.id;
                }

                for (const rel of inferred) {
                // Remap source/target using current canvas bindings
                const sourceEntityId = modelToEntity[rel.source] || rel.source;
                const targetEntityId = modelToEntity[rel.target] || rel.target;

                // Check if this relationship involves the current entity
                if (sourceEntityId !== id && targetEntityId !== id) continue;

                // Check if both entities exist on the canvas
                const sourceExists = $nodes.some(
                    (n) => n.id === sourceEntityId,
                );
                const targetExists = $nodes.some(
                    (n) => n.id === targetEntityId,
                );
                if (!sourceExists || !targetExists) continue;

                // Remap the relationship to use entity IDs
                const remappedRel = {
                    ...rel,
                    source: sourceEntityId,
                    target: targetEntityId,
                };

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
        type: "width" | "height",
    ) {
        event.stopPropagation();
        event.preventDefault();

        const startX = event.clientX;
        const startY = event.clientY;
        const initialWidth = nodeWidth;
        const initialHeight = columnPanelHeight;

        function onMove(moveEvent: PointerEvent) {
            if (type === "width") {
                const delta = moveEvent.clientX - startX;
                const next = Math.min(
                    MAX_WIDTH,
                    Math.max(MIN_WIDTH, initialWidth + delta),
                );
                updateNodeData(id, { width: next });
            } else {
                const delta = moveEvent.clientY - startY;
                const next = Math.min(
                    MAX_PANEL_HEIGHT,
                    Math.max(MIN_PANEL_HEIGHT, initialHeight + delta),
                );
                updateNodeData(id, { panelHeight: next });
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
        updateNodeData(id, { dbt_model: null });

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

    function toggleCollapse(event: Event) {
        // Only toggle if clicking on the header background, not on the input
        if ((event.target as HTMLElement).tagName === "INPUT") {
            return;
        }
        updateNodeData(id, { collapsed: !isCollapsed });
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
        showDeleteModal = true;
    }

    function deleteEntity() {
        try {
            // Remove all edges that reference this node
            edges.update((list) =>
                list.filter((edge) => edge.source !== id && edge.target !== id),
            );

            // Remove the node itself
            nodes.update((list) => list.filter((node) => node.id !== id));

            showDeleteModal = false;
        } catch (error) {
            console.error("Failed to delete entity:", error);
            alert("Failed to delete entity. Please try again.");
            showDeleteModal = false;
        }
    }

    function cancelDelete() {
        showDeleteModal = false;
    }

    // Entity type menu functionality
    function toggleEntityTypeMenu() {
        showEntityTypeMenu = !showEntityTypeMenu;
    }

    function closeEntityTypeMenu() {
        showEntityTypeMenu = false;
    }

    async function setEntityType(newType: "fact" | "dimension" | "unclassified") {
        try {
            // Update node data locally
            updateNodeData(id, { entity_type: newType });
            closeEntityTypeMenu();
        } catch (error) {
            console.error("Failed to update entity type:", error);
            alert("Failed to update entity type. Please try again.");
        }
    }

    // Tag editing functionality
    let entityTags = $derived(normalizeTags(data.tags));
    let tagInput = $state("");
    let showTagInput = $state(false);

    function getCurrentTags(nodeId: string): string[] {
        const node = $nodes.find((n) => n.id === nodeId);
        return normalizeTags(node?.data?.tags);
    }

    function addTag(tag: string) {
        const trimmed = tag.trim();
        if (!trimmed) return;

        const currentTags = getCurrentTags(id);
        if (currentTags.includes(trimmed)) return;

        // When user adds a tag, add it to both display tags and schema tags
        const currentSchemaTags = normalizeTags(data._schemaTags);
        updateNodeData(id, { 
            tags: [...currentTags, trimmed],
            _schemaTags: [...currentSchemaTags, trimmed]
        });
        if (isBound) {
            hasUnsavedChanges = true;
        }
        tagInput = "";
    }

    function removeTag(tag: string) {
        const newTags = entityTags.filter((t) => t !== tag);
        // Also remove from schema tags if present
        const currentSchemaTags = normalizeTags(data._schemaTags);
        const newSchemaTags = currentSchemaTags.filter((t) => t !== tag);
        
        updateNodeData(id, { 
            tags: newTags,
            _schemaTags: newSchemaTags
        });
        if (isBound) {
            hasUnsavedChanges = true;
        }
    }

    function handleTagInputKeydown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            e.preventDefault();
            if (tagInput.trim()) {
                addTag(tagInput);
            }
        } else if (e.key === "Escape") {
            tagInput = "";
            showTagInput = false;
        } else if (e.key === ",") {
            e.preventDefault();
            const parts = tagInput.split(",");
            parts.forEach((part) => {
                if (part.trim()) {
                    addTag(part.trim());
                }
            });
            tagInput = "";
        }
    }

    function handleTagInputBlur() {
        if (tagInput.trim()) {
            if (isBatchEditing) {
                addTagToBatch(tagInput);
            } else {
                addTag(tagInput);
            }
        }
        showTagInput = false;
    }

    function addTagToBatch(tag: string) {
        const trimmed = tag.trim();
        if (!trimmed) return;
        
        const allSelectedIds = [id, ...selectedEntityNodes.map((n) => n.id)];
        allSelectedIds.forEach((nodeId) => {
            const node = $nodes.find((n) => n.id === nodeId);
            const currentTags = getCurrentTags(nodeId);
            if (!currentTags.includes(trimmed)) {
                const currentSchemaTags = normalizeTags(node?.data?._schemaTags);
                updateNodeData(nodeId, { 
                    tags: [...currentTags, trimmed],
                    _schemaTags: [...currentSchemaTags, trimmed]
                });
                // If this is the current node and it's bound, mark as having unsaved changes
                if (nodeId === id && isBound) {
                    hasUnsavedChanges = true;
                }
            }
        });
        tagInput = "";
    }

    function removeTagFromBatch(tag: string) {
        const allSelectedIds = [id, ...selectedEntityNodes.map((n) => n.id)];
        allSelectedIds.forEach((nodeId) => {
            const node = $nodes.find((n) => n.id === nodeId);
            if (node && node.type === "entity") {
                const currentTags = normalizeTags(node.data?.tags);
                const newTags = currentTags.filter((t) => t !== tag);
                const currentSchemaTags = normalizeTags(node.data?._schemaTags);
                const newSchemaTags = currentSchemaTags.filter((t) => t !== tag);
                updateNodeData(nodeId, { 
                    tags: newTags,
                    _schemaTags: newSchemaTags
                });
                // If this is the current node and it's bound, mark as having unsaved changes
                if (nodeId === id && isBound) {
                    hasUnsavedChanges = true;
                }
            }
        });
    }

    function handleBatchTagInputKeydown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            e.preventDefault();
            if (tagInput.trim()) {
                addTagToBatch(tagInput);
            }
        } else if (e.key === "Escape") {
            tagInput = "";
            showTagInput = false;
        } else if (e.key === ",") {
            e.preventDefault();
            const parts = tagInput.split(",");
            parts.forEach((part) => {
                if (part.trim()) {
                    addTagToBatch(part.trim());
                }
            });
            tagInput = "";
        }
    }

    // Field drafting functionality
    let draftedFields = $derived((data.drafted_fields || []) as DraftedField[]);

    function addDraftedField() {
        const newField: DraftedField = {
            name: "",
            datatype: "text",
        };
        const updatedFields = [...draftedFields, newField];
        updateNodeData(id, { drafted_fields: updatedFields });
    }

    function updateDraftedField(index: number, updates: Partial<DraftedField>) {
        const updatedFields = draftedFields.map((field, i) =>
            i === index ? { ...field, ...updates } : field,
        );
        updateNodeData(id, { drafted_fields: updatedFields });
    }

    function deleteDraftedField(index: number) {
        const updatedFields = draftedFields.filter((_, i) => i !== index);
        updateNodeData(id, { drafted_fields: updatedFields });
    }

    // Drag-and-drop for field linking
    function onFieldDragStart(fieldName: string, e: DragEvent) {
        e.stopPropagation(); // Prevent node drag
        if (!e.dataTransfer) return;
        e.dataTransfer.effectAllowed = "link";
        e.dataTransfer.setData("text/plain", fieldName); // Required for drag to work

        $draggingField = {
            nodeId: id,
            fieldName: fieldName,
            nodeLabel: data.label || id,
        };
    }

    function onFieldDragEnd(e: DragEvent) {
        e.stopPropagation();
        $draggingField = null;
    }

    function onFieldDragOver(e: DragEvent) {
        if (!$draggingField) return;
        if ($draggingField.nodeId === id) return; // Same entity, no link
        e.preventDefault();
        e.stopPropagation(); // Prevent bubble to canvas
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = "link";
        }
    }

    async function onFieldDrop(targetFieldName: string, e: DragEvent) {
        e.preventDefault();
        e.stopPropagation(); // Prevent bubble to canvas
        if (!$draggingField || $draggingField.nodeId === id) return;

        // Find or create an edge between the two entities
        const sourceNodeId = $draggingField.nodeId;
        const targetNodeId = id;

        // Check for existing edge with same source, target, and fields
        const exists = $edges.some(
            (e) =>
                e.source === sourceNodeId &&
                e.target === targetNodeId &&
                e.data?.source_field === $draggingField?.fieldName &&
                e.data?.target_field === targetFieldName,
        );

        if (exists) {
            console.warn("Blocked duplicate field connection");
            $draggingField = null;
            return;
        }

        // Check for generic edge to reuse (any direction)
        // A generic edge has no source_field/target_field defined
        const genericEdge = $edges.find(
            (e) =>
                ((e.source === sourceNodeId && e.target === targetNodeId) ||
                    (e.source === targetNodeId && e.target === sourceNodeId)) &&
                !e.data?.source_field &&
                !e.data?.target_field,
        );

        if (genericEdge) {
            // Reuse this edge, enforcing the direction of the field drag
            $edges = $edges.map((e) => {
                if (e.id === genericEdge.id) {
                    return {
                        ...e,
                        source: sourceNodeId,
                        target: targetNodeId,
                        data: {
                            ...e.data,
                            source_field: $draggingField!.fieldName,
                            target_field: targetFieldName,
                        },
                    };
                }
                return e;
            });
            $draggingField = null;
            return;
        }

        // Get active model information for source and target nodes (prefer ephemeral active model data)
        const sourceNodeData = $nodes.find(n => n.id === sourceNodeId)?.data as any;
        const targetNodeData = $nodes.find(n => n.id === targetNodeId)?.data as any;
        
        const sourceActiveModel = (() => {
            if (sourceNodeData?._activeModelName) {
                return {
                    name: sourceNodeData._activeModelName as string,
                    version: sourceNodeData._activeModelVersion as number | null | undefined,
                };
            }
            if (sourceNodeData?.dbt_model) {
                return $dbtModels.find(m => m.unique_id === sourceNodeData.dbt_model) || null;
            }
            const firstAdditional = (sourceNodeData?.additional_models as string[] | undefined)?.[0] || null;
            if (firstAdditional) {
                return $dbtModels.find(m => m.unique_id === firstAdditional) || null;
            }
            return null;
        })();
        
        const targetActiveModel = (() => {
            if (targetNodeData?._activeModelName) {
                return {
                    name: targetNodeData._activeModelName as string,
                    version: targetNodeData._activeModelVersion as number | null | undefined,
                };
            }
            if (targetNodeData?.dbt_model) {
                return $dbtModels.find(m => m.unique_id === targetNodeData.dbt_model) || null;
            }
            const firstAdditional = (targetNodeData?.additional_models as string[] | undefined)?.[0] || null;
            if (firstAdditional) {
                return $dbtModels.find(m => m.unique_id === firstAdditional) || null;
            }
            return null;
        })();
        
        /**
         * Relationship Direction Rules:
         * 
         * Relationships must always be named from the "1" side to the "*" side (parent → child).
         * - one_to_many: source = 1 (parent), target = * (child)
         * - many_to_one: source = * (child), target = 1 (parent)
         * - one_to_one: source = FK holder, target = referenced table
         * 
         * Auto-Detection from dbt:
         * When both entities have bound dbt models, we detect FK/PK semantics to determine parent/child:
         * - If source field is FK and target field is PK → flip direction (FK points to PK, so PK is parent)
         * - If source field is PK and target field is FK → keep direction (PK is parent, FK is child)
         * - Otherwise → use drag direction as fallback
         * 
         * Manual Override:
         * Users can manually swap direction using the swap button in the relationship editor.
         */
        
        // Detect FK/PK semantics if both models are bound
        let finalSource = sourceNodeId;
        let finalTarget = targetNodeId;
        let finalSourceField = $draggingField.fieldName;
        let finalTargetField = targetFieldName;
        let relationshipType: 'one_to_many' | 'many_to_one' | 'one_to_one' | 'many_to_many' = 'one_to_many';
        
        if (sourceActiveModel && targetActiveModel) {
            try {
                // Fetch schemas for both models to detect FK/PK semantics
                const sourceSchema = await getModelSchema(
                    sourceActiveModel.name,
                    sourceActiveModel.version ?? undefined
                );
                const targetSchema = await getModelSchema(
                    targetActiveModel.name,
                    targetActiveModel.version ?? undefined
                );
                
                if (sourceSchema && targetSchema) {
                    // Build map of model schemas for FK/PK detection
                    const modelSchemas = new Map<string, any>();
                    modelSchemas.set(sourceActiveModel.name, sourceSchema);
                    modelSchemas.set(targetActiveModel.name, targetSchema);
                    
                    // Detect semantics for both fields
                    const sourceSemantics = detectFieldSemantics(
                        sourceActiveModel.name,
                        finalSourceField,
                        targetActiveModel.name,
                        modelSchemas
                    );
                    const targetSemantics = detectFieldSemantics(
                        targetActiveModel.name,
                        finalTargetField,
                        sourceActiveModel.name,
                        modelSchemas
                    );
                    
                    // Determine if direction needs to be flipped to maintain 1 → * rule
                    // Rule: Relationships always go from parent (PK holder) to child (FK holder)
                    if (sourceSemantics === 'fk' && targetSemantics === 'pk') {
                        // Flip direction: FK → PK becomes PK → FK (parent → child)
                        // The FK field is on the child side, PK field is on the parent side
                        finalSource = targetNodeId;
                        finalTarget = sourceNodeId;
                        finalSourceField = targetFieldName;
                        finalTargetField = $draggingField.fieldName;
                        relationshipType = 'one_to_many'; // PK → FK = one_to_many (parent → child)
                    } else if (sourceSemantics === 'pk' && targetSemantics === 'fk') {
                        // Keep direction: PK → FK is already correct (parent → child)
                        relationshipType = 'one_to_many';
                    } else {
                        // Unknown semantics or both PKs/FKs: use drag direction as fallback
                        // This handles edge cases like:
                        // - Both fields are PKs (likely many-to-many or one-to-one)
                        // - Both fields are FKs (unusual case)
                        // - No FK/PK information available
                        relationshipType = 'one_to_many';
                    }
                }
            } catch (error) {
                // Fall back to drag direction on error (e.g., schema fetch fails, network error)
                // This ensures relationship creation doesn't fail even if FK/PK detection fails
                console.warn('Error detecting FK/PK semantics, using drag direction:', error);
            }
        }
        // If models aren't bound (greenfield), use drag direction - user can manually swap if needed
        
        // Create relationship object
        const relationship = {
            source: finalSource,
            target: finalTarget,
            label: "",
            type: relationshipType,
            source_field: finalSourceField,
            target_field: finalTargetField,
            source_model_name: finalSource === sourceNodeId ? sourceActiveModel?.name : targetActiveModel?.name,
            source_model_version: finalSource === sourceNodeId ? (sourceActiveModel?.version ?? null) : (targetActiveModel?.version ?? null),
            target_model_name: finalTarget === targetNodeId ? targetActiveModel?.name : sourceActiveModel?.name,
            target_model_version: finalTarget === targetNodeId ? (targetActiveModel?.version ?? null) : (sourceActiveModel?.version ?? null),
        };
        
        // Merge relationship into edges (will aggregate by entity pair)
        $edges = mergeRelationshipIntoEdges($edges, relationship);

        $draggingField = null;
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
    <Handle type="target" position={Position.Top} id="top-target" class="!bg-gray-400 !w-2 !h-2" />
    <Handle type="source" position={Position.Top} id="top-source" class="!bg-gray-400 !w-2 !h-2" />
    
    <!-- Left -->
    <Handle type="target" position={Position.Left} id="left-target" class="!bg-gray-400 !w-2 !h-2" />
    <Handle type="source" position={Position.Left} id="left-source" class="!bg-gray-400 !w-2 !h-2" />
    
    <!-- Right -->
    <Handle type="target" position={Position.Right} id="right-target" class="!bg-gray-400 !w-2 !h-2" />
    <Handle type="source" position={Position.Right} id="right-source" class="!bg-gray-400 !w-2 !h-2" />
    
    <!-- Bottom -->
    <Handle type="target" position={Position.Bottom} id="bottom-target" class="!bg-gray-400 !w-2 !h-2" />
    <Handle type="source" position={Position.Bottom} id="bottom-source" class="!bg-gray-400 !w-2 !h-2" />

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
            <!-- Entity Type Badge -->
            {#if data.entity_type}
                <div
                    class="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0"
                    class:bg-blue-100={data.entity_type === 'fact'}
                    class:bg-green-100={data.entity_type === 'dimension'}
                    class:bg-gray-100={data.entity_type === 'unclassified'}
                    class:text-blue-700={data.entity_type === 'fact'}
                    class:text-green-700={data.entity_type === 'dimension'}
                    class:text-gray-700={data.entity_type === 'unclassified'}
                    class:cursor-pointer={true}
                    class:opacity-80={true}
                    onclick={(e) => { e.stopPropagation(); toggleEntityTypeMenu(); }}
                    title={data.entity_type === 'fact'
                        ? 'Fact: Transaction table containing measures and keys (click to change)'
                        : data.entity_type === 'dimension'
                        ? 'Dimension: Descriptive table with attributes (click to change)'
                        : 'Unclassified: Generic entity (click to change)'}
                >
                    <Icon
                        icon="lucide:tag"
                        class="w-3 h-3"
                    />
                    <span class="uppercase">{data.entity_type}</span>
                </div>
            {/if}
            <input
                type="text"
                value={data.label}
                oninput={updateLabel}
                onblur={updateIdFromLabel}
                onclick={(e) => e.stopPropagation()}
                ondblclick={(e) => e.stopPropagation()}
                onkeydown={(e) => e.stopPropagation()}
                onkeyup={(e) => e.stopPropagation()}
                class="font-bold bg-transparent w-full focus:outline-none focus:bg-white focus:ring-1 focus:ring-primary-500 rounded px-1.5 py-0.5 text-sm text-gray-800"
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
                        onclick={() => openLineageModal(boundModelName)}
                        aria-label="Show lineage for {boundModelName}"
                        class="text-gray-400 hover:text-primary-600 transition-colors px-1.5 py-0.5 rounded hover:bg-primary-50 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        title="Show lineage"
                    >
                        <Icon icon="lucide:git-branch" class="w-4 h-4" />
                    </button>
                {/if}
                {#if exposuresEnabled}
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
                    title="Draft mode (not bound to dbt model)"
                ></div>
                {#if exposuresEnabled}
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

    <!-- Entity Type Dropdown Menu -->
    {#if showEntityTypeMenu}
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
                <Icon icon="lucide:tag" class="w-4 h-4 text-blue-600" />
                <span>Set as Fact</span>
            </button>
            <button
                onclick={() => setEntityType('dimension')}
                class="w-full px-3 py-2 flex items-center gap-2 hover:bg-green-50 text-left transition-colors"
                role="menuitem"
            >
                <Icon icon="lucide:tag" class="w-4 h-4 text-green-600" />
                <span>Set as Dimension</span>
            </button>
            <button
                onclick={() => setEntityType('unclassified')}
                class="w-full px-3 py-2 flex items-center gap-2 hover:bg-gray-50 text-left transition-colors"
                role="menuitem"
            >
                <Icon icon="lucide:tag" class="w-4 h-4 text-gray-500" />
                <span>Set as Unclassified</span>
            </button>
        </div>
    {/if}

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
                                title="Drag a dbt model from the sidebar to add it"
                            >
                                <Icon icon="lucide:plus" class="w-3 h-3" />
                            </button>
                        </div>
                    {/if}

                    <!-- Tags Editor -->
                    <div class="mb-2.5">
                        {#if isBatchEditing}
                            <div class="mb-1 px-1.5 py-1 bg-purple-50 border border-purple-200 rounded text-[10px] text-purple-700 flex items-center gap-1">
                                <Icon icon="lucide:layers" class="w-3 h-3" />
                                Batch editing {selectedEntityNodes.length + 1} entities
                            </div>
                        {/if}
                        <div class="flex items-center gap-2 flex-wrap mb-1">
                            <span
                                class="font-medium text-[10px] uppercase tracking-wider text-gray-500"
                                >Tags</span
                            >
                            {#each entityTags as tag}
                                <span
                                    class="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] border border-blue-100 flex items-center gap-1 group"
                                >
                                    {tag}
                                    <button
                                        onclick={() => isBatchEditing ? removeTagFromBatch(tag) : removeTag(tag)}
                                        class="opacity-0 group-hover:opacity-100 transition-opacity text-blue-500 hover:text-blue-700"
                                        title={isBatchEditing ? "Remove tag from all selected" : "Remove tag"}
                                    >
                                        <Icon icon="lucide:x" class="w-2.5 h-2.5" />
                                    </button>
                                </span>
                            {/each}
                            {#if !showTagInput}
                                <button
                                    onclick={() => {
                                        showTagInput = true;
                                        setTimeout(() => {
                                            const input = document.getElementById(`tag-input-${id}`) as HTMLInputElement;
                                            input?.focus();
                                        }, 0);
                                    }}
                                    class="px-1.5 py-0.5 text-blue-600 hover:bg-blue-50 rounded text-[10px] border border-blue-200 transition-colors flex items-center gap-1"
                                    title={isBatchEditing ? "Add tag to all selected" : "Add tag"}
                                >
                                    <Icon icon="lucide:plus" class="w-2.5 h-2.5" />
                                    Add
                                </button>
                            {/if}
                        </div>
                        {#if showTagInput}
                            <input
                                id="tag-input-{id}"
                                type="text"
                                bind:value={tagInput}
                                onkeydown={isBatchEditing ? handleBatchTagInputKeydown : handleTagInputKeydown}
                                onblur={handleTagInputBlur}
                                placeholder={isBatchEditing ? "Enter tag for all selected (comma or Enter)" : "Enter tag (comma or Enter to add)"}
                                class="w-full px-1.5 py-0.5 text-[10px] border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                                onclick={(e) => e.stopPropagation()}
                            />
                        {/if}
                    </div>

                    {#if schemaLoading}
                        <div
                            class="text-center text-gray-400 py-4 text-[10px] italic"
                        >
                            Loading schema...
                        </div>
                    {:else}
                        <div
                            class="overflow-y-auto border border-gray-200 rounded-md bg-white p-1 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent nodrag"
                            style={`max-height:${columnPanelHeight}px`}
                        >
                            {#if editableColumns.length > 0}
                                {#each editableColumns as col, index}
                                    <div
                                        class="p-1.5 border-b border-gray-100 last:border-0 bg-white rounded mb-1 relative group hover:bg-gray-50"
                                        class:bg-blue-50={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-2={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-blue-300={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        ondragover={onFieldDragOver}
                                        ondrop={(e) => onFieldDrop(col.name, e)}
                                        role="presentation"
                                    >
                                        <div
                                            class="flex gap-1.5 mb-1 items-center"
                                        >
                                            <span
                                                class="text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity text-xs select-none cursor-grab nodrag hover:text-primary-500 pt-1"
                                                draggable="true"
                                                onmousedown={(e) =>
                                                    e.stopPropagation()}
                                                onpointerdown={(e) =>
                                                    e.stopPropagation()}
                                                ondragstart={(e) =>
                                                    onFieldDragStart(
                                                        col.name,
                                                        e,
                                                    )}
                                                ondragend={onFieldDragEnd}
                                                class:cursor-grabbing={$draggingField?.nodeId ===
                                                    id &&
                                                    $draggingField?.fieldName ===
                                                        col.name}
                                                title="Drag to link to another field"
                                                role="presentation"
                                                aria-hidden="true"
                                                tabindex="-1"
                                            >
                                                <Icon
                                                    icon="lucide:link"
                                                    class="w-3 h-3"
                                                />
                                            </span>
                                            <div
                                                class="flex-1 flex flex-col gap-1"
                                            >
                                                <div
                                                    class="flex items-center gap-1"
                                                >
                                                    <input
                                                        type="text"
                                                        value={col.name}
                                                        oninput={(e) =>
                                                            updateEditableColumn(
                                                                index,
                                                                {
                                                                    name: (
                                                                        e.target as HTMLInputElement
                                                                    ).value,
                                                                },
                                                            )}
                                                        class="flex-1 px-1.5 py-0.5 text-xs border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 font-medium"
                                                        placeholder="column_name"
                                                    />
                                                    <input
                                                        type="text"
                                                        value={col.data_type ||
                                                            ""}
                                                        oninput={(e) =>
                                                            updateEditableColumn(
                                                                index,
                                                                {
                                                                    data_type: (
                                                                        e.target as HTMLInputElement
                                                                    ).value,
                                                                },
                                                            )}
                                                        class="w-20 px-1 py-0.5 text-[10px] border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 uppercase text-gray-600 font-mono"
                                                        placeholder="text"
                                                    />
                                                    <button
                                                        onclick={() =>
                                                            deleteEditableColumn(
                                                                index,
                                                            )}
                                                        class="text-gray-400 hover:text-danger-600 p-1 rounded hover:bg-danger-50"
                                                        title="Delete column"
                                                    >
                                                        <Icon
                                                            icon="lucide:x"
                                                            class="w-3 h-3"
                                                        />
                                                    </button>
                                                </div>
                                                <input
                                                    type="text"
                                                    value={col.description ||
                                                        ""}
                                                    oninput={(e) =>
                                                        updateEditableColumn(
                                                            index,
                                                            {
                                                                description: (
                                                                    e.target as HTMLInputElement
                                                                ).value,
                                                            },
                                                        )}
                                                    class="w-full px-0 text-[10px] text-gray-500 bg-transparent focus:outline-none border-none placeholder:text-gray-300"
                                                    placeholder="Description (optional)"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                {/each}
                            {:else}
                                <div
                                    class="text-center text-gray-400 py-4 text-[10px] italic"
                                >
                                    No columns defined
                                </div>
                            {/if}
                        </div>

                        <button
                            onclick={addEditableColumn}
                            class="mt-2 w-full text-xs text-primary-600 hover:bg-primary-50 p-1.5 rounded border border-primary-200 transition-colors font-medium flex items-center justify-center gap-1"
                        >
                            <Icon icon="lucide:plus" class="w-3 h-3" /> Add Column
                        </button>

                        {#if schemaError}
                            <div
                                class="mt-2 p-2 bg-danger-50 border border-danger-200 rounded text-danger-800 text-[10px]"
                            >
                                {schemaError}
                            </div>
                        {/if}

                        <div class="flex gap-2 mt-2">
                            <button
                                onclick={saveSchema}
                                disabled={!hasUnsavedChanges || schemaSaving}
                                class="flex-1 text-[10px] font-medium p-1.5 rounded border transition-colors flex items-center justify-center gap-1"
                                class:text-primary-600={hasUnsavedChanges &&
                                    !schemaSaving}
                                class:hover:bg-primary-50={hasUnsavedChanges &&
                                    !schemaSaving}
                                class:border-primary-200={hasUnsavedChanges &&
                                    !schemaSaving}
                                class:text-gray-400={!hasUnsavedChanges ||
                                    schemaSaving}
                                class:border-gray-200={!hasUnsavedChanges ||
                                    schemaSaving}
                                class:cursor-not-allowed={!hasUnsavedChanges ||
                                    schemaSaving}
                            >
                                {#if schemaSaving}
                                    <Icon
                                        icon="lucide:loader-2"
                                        class="w-3 h-3 animate-spin"
                                    />
                                    Saving...
                                {:else}
                                    <Icon icon="lucide:save" class="w-3 h-3" />
                                    Save to YAML
                                {/if}
                            </button>
                            <button
                                class="text-[10px] text-danger-500 hover:bg-danger-50 p-1.5 rounded border border-danger-100 transition-colors font-medium"
                                onclick={unbind}
                            >
                                Unbind
                            </button>
                        </div>
                    {/if}
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

                        <!-- Tags Editor for Unbound Entities -->
                        <div class="mb-2.5">
                            {#if isBatchEditing}
                                <div class="mb-1 px-1.5 py-1 bg-purple-50 border border-purple-200 rounded text-[10px] text-purple-700 flex items-center gap-1">
                                    <Icon icon="lucide:layers" class="w-3 h-3" />
                                    Batch editing {selectedEntityNodes.length + 1} entities
                                </div>
                            {/if}
                            <div class="flex items-center gap-2 flex-wrap mb-1">
                                <span
                                    class="font-medium text-[10px] uppercase tracking-wider text-gray-500"
                                    >Tags</span
                                >
                                {#each entityTags as tag}
                                    <span
                                        class="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] border border-blue-100 flex items-center gap-1 group"
                                    >
                                        {tag}
                                        <button
                                            onclick={() => isBatchEditing ? removeTagFromBatch(tag) : removeTag(tag)}
                                            class="opacity-0 group-hover:opacity-100 transition-opacity text-blue-500 hover:text-blue-700"
                                            title={isBatchEditing ? "Remove tag from all selected" : "Remove tag"}
                                        >
                                            <Icon icon="lucide:x" class="w-2.5 h-2.5" />
                                        </button>
                                    </span>
                                {/each}
                                {#if !showTagInput}
                                    <button
                                        onclick={() => {
                                            showTagInput = true;
                                            setTimeout(() => {
                                                const input = document.getElementById(`tag-input-unbound-${id}`) as HTMLInputElement;
                                                input?.focus();
                                            }, 0);
                                        }}
                                        class="px-1.5 py-0.5 text-blue-600 hover:bg-blue-50 rounded text-[10px] border border-blue-200 transition-colors flex items-center gap-1"
                                        title={isBatchEditing ? "Add tag to all selected" : "Add tag"}
                                    >
                                        <Icon icon="lucide:plus" class="w-2.5 h-2.5" />
                                        Add
                                    </button>
                                {/if}
                            </div>
                            {#if showTagInput}
                                <input
                                    id="tag-input-unbound-{id}"
                                    type="text"
                                    bind:value={tagInput}
                                    onkeydown={isBatchEditing ? handleBatchTagInputKeydown : handleTagInputKeydown}
                                    onblur={handleTagInputBlur}
                                    placeholder={isBatchEditing ? "Enter tag for all selected (comma or Enter)" : "Enter tag (comma or Enter to add)"}
                                    class="w-full px-1.5 py-0.5 text-[10px] border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                                    onclick={(e) => e.stopPropagation()}
                                />
                            {/if}
                        </div>

                        <div
                            class="overflow-y-auto border border-gray-200 rounded-md bg-white p-1 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent nodrag"
                            style={`max-height:${columnPanelHeight}px`}
                        >
                            {#if draftedFields.length > 0}
                                {#each draftedFields as field, index}
                                    <div
                                        class="p-1.5 border-b border-gray-100 last:border-0 bg-white rounded mb-1 relative group hover:bg-gray-50"
                                        class:bg-blue-50={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-2={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-blue-300={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        ondragover={onFieldDragOver}
                                        ondrop={(e) =>
                                            onFieldDrop(field.name, e)}
                                        role="presentation"
                                    >
                                        <div
                                            class="flex gap-1.5 mb-1 items-center"
                                        >
                                            <span
                                                class="text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity text-xs select-none cursor-grab nodrag hover:text-primary-500 pt-1"
                                                draggable="true"
                                                onmousedown={(e) =>
                                                    e.stopPropagation()}
                                                onpointerdown={(e) =>
                                                    e.stopPropagation()}
                                                ondragstart={(e) =>
                                                    onFieldDragStart(
                                                        field.name,
                                                        e,
                                                    )}
                                                ondragend={onFieldDragEnd}
                                                class:cursor-grabbing={$draggingField?.nodeId ===
                                                    id &&
                                                    $draggingField?.fieldName ===
                                                        field.name}
                                                title="Drag to link to another field"
                                                role="presentation"
                                                aria-hidden="true"
                                                tabindex="-1"
                                            >
                                                <Icon
                                                    icon="lucide:link"
                                                    class="w-3 h-3"
                                                />
                                            </span>
                                            <div
                                                class="flex-1 flex flex-col gap-1"
                                            >
                                                <div
                                                    class="flex items-center gap-1"
                                                >
                                                    <input
                                                        type="text"
                                                        value={field.name}
                                                        oninput={(e) =>
                                                            updateDraftedField(
                                                                index,
                                                                {
                                                                    name: (
                                                                        e.target as HTMLInputElement
                                                                    ).value,
                                                                },
                                                            )}
                                                        class="flex-1 px-1.5 py-0.5 text-xs border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 font-medium"
                                                        placeholder="field_name"
                                                    />
                                                    <select
                                                        value={field.datatype}
                                                        onchange={(e) =>
                                                            updateDraftedField(
                                                                index,
                                                                {
                                                                    datatype: (
                                                                        e.target as HTMLSelectElement
                                                                    )
                                                                        .value as any,
                                                                },
                                                            )}
                                                        class="w-20 px-1 py-0.5 text-[10px] border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 uppercase text-gray-600 font-mono"
                                                    >
                                                        <option value="text"
                                                            >text</option
                                                        >
                                                        <option value="int"
                                                            >int</option
                                                        >
                                                        <option value="float"
                                                            >float</option
                                                        >
                                                        <option value="bool"
                                                            >bool</option
                                                        >
                                                        <option value="date"
                                                            >date</option
                                                        >
                                                        <option
                                                            value="timestamp"
                                                            >timestamp</option
                                                        >
                                                    </select>
                                                    <button
                                                        onclick={() =>
                                                            deleteDraftedField(
                                                                index,
                                                            )}
                                                        class="text-gray-400 hover:text-danger-600 p-1 rounded hover:bg-danger-50"
                                                        title="Delete field"
                                                    >
                                                        <Icon
                                                            icon="lucide:x"
                                                            class="w-3 h-3"
                                                        />
                                                    </button>
                                                </div>
                                                <input
                                                    type="text"
                                                    value={field.description ||
                                                        ""}
                                                    oninput={(e) =>
                                                        updateDraftedField(
                                                            index,
                                                            {
                                                                description: (
                                                                    e.target as HTMLInputElement
                                                                ).value,
                                                            },
                                                        )}
                                                    class="w-full px-0 text-[10px] text-gray-500 bg-transparent focus:outline-none border-none placeholder:text-gray-300"
                                                    placeholder="Description (optional)"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                {/each}
                            {:else}
                                <div
                                    class="text-center text-gray-400 py-4 text-[10px] italic"
                                >
                                    No fields defined
                                </div>
                            {/if}
                        </div>

                        <button
                            onclick={addDraftedField}
                            class="mt-2 w-full text-xs text-primary-600 hover:bg-primary-50 p-1.5 rounded border border-primary-200 transition-colors font-medium flex items-center justify-center gap-1"
                        >
                            <Icon icon="lucide:plus" class="w-3 h-3" /> Add Field
                        </button>
                    </div>
                {:else}
                    <!-- Conceptual View -->
                    <textarea
                        value={data.description || ""}
                        oninput={updateDescription}
                        class="w-full text-xs text-gray-600 resize-y min-h-[60px] bg-gray-50 focus:outline-none focus:bg-white focus:ring-1 focus:ring-primary-500 rounded p-1.5 border border-gray-200"
                        placeholder="Description..."
                    ></textarea>

                    <!-- Tags Editor for Unbound Entities (Conceptual View) -->
                    <div class="mt-2.5">
                        {#if isBatchEditing}
                            <div class="mb-1 px-1.5 py-1 bg-purple-50 border border-purple-200 rounded text-[10px] text-purple-700 flex items-center gap-1">
                                <Icon icon="lucide:layers" class="w-3 h-3" />
                                Batch editing {selectedEntityNodes.length + 1} entities
                            </div>
                        {/if}
                        <div class="flex items-center gap-2 flex-wrap mb-1">
                            <span
                                class="font-medium text-[10px] uppercase tracking-wider text-gray-500"
                                >Tags</span
                            >
                            {#each entityTags as tag}
                                <span
                                    class="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] border border-blue-100 flex items-center gap-1 group"
                                >
                                    {tag}
                                    <button
                                        onclick={() => isBatchEditing ? removeTagFromBatch(tag) : removeTag(tag)}
                                        class="opacity-0 group-hover:opacity-100 transition-opacity text-blue-500 hover:text-blue-700"
                                        title={isBatchEditing ? "Remove tag from all selected" : "Remove tag"}
                                    >
                                        <Icon icon="lucide:x" class="w-2.5 h-2.5" />
                                    </button>
                                </span>
                            {/each}
                            {#if !showTagInput}
                                <button
                                    onclick={() => {
                                        showTagInput = true;
                                        setTimeout(() => {
                                            const input = document.getElementById(`tag-input-conceptual-${id}`) as HTMLInputElement;
                                            input?.focus();
                                        }, 0);
                                    }}
                                    class="px-1.5 py-0.5 text-blue-600 hover:bg-blue-50 rounded text-[10px] border border-blue-200 transition-colors flex items-center gap-1"
                                    title={isBatchEditing ? "Add tag to all selected" : "Add tag"}
                                >
                                    <Icon icon="lucide:plus" class="w-2.5 h-2.5" />
                                    Add
                                </button>
                            {/if}
                        </div>
                        {#if showTagInput}
                            <input
                                id="tag-input-conceptual-{id}"
                                type="text"
                                bind:value={tagInput}
                                onkeydown={isBatchEditing ? handleBatchTagInputKeydown : handleTagInputKeydown}
                                onblur={handleTagInputBlur}
                                placeholder={isBatchEditing ? "Enter tag for all selected (comma or Enter)" : "Enter tag (comma or Enter to add)"}
                                class="w-full px-1.5 py-0.5 text-[10px] border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                                onclick={(e) => e.stopPropagation()}
                            />
                        {/if}
                    </div>
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
                            Drag dbt model here
                        </div>
                    {/if}
                {/if}
            {/if}
        </div>
    {/if}


    <div
        class="width-resize-handle"
        onpointerdown={(event) => startDimensionResize(event, "width")}
        title="Drag to resize width"
    ></div>

    {#if $viewMode === "logical"}
        <div
            class="height-resize-handle"
            onpointerdown={(event) => startDimensionResize(event, "height")}
            title="Drag to show more columns"
        ></div>
    {/if}
</div>

<DeleteConfirmModal
    open={showDeleteModal}
    entityLabel={data.label || "Entity"}
    onConfirm={deleteEntity}
    onCancel={cancelDelete}
/>

<UndescribedAttributesWarningModal
    open={showUndescribedAttributesWarning}
    attributeNames={undescribedAttributeNames}
    onConfirm={handleWarningConfirm}
    onCancel={handleWarningCancel}
/>

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

    .height-resize-handle {
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 100%;
        height: 6px;
        cursor: ns-resize;
        border-radius: 999px;
    }
</style>
