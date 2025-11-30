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
    } from "$lib/stores";
    import type { DbtModel, DraftedField, ModelSchemaColumn } from "$lib/types";
    import {
        inferRelationships,
        getModelSchema,
        updateModelSchema,
    } from "$lib/api";
    import DeleteConfirmModal from "./DeleteConfirmModal.svelte";
    import Icon from "@iconify/svelte";

    type $$Props = NodeProps;

    let { data, id, selected } = $props<$$Props>();

    const { updateNodeData } = useSvelteFlow();
    let showDeleteModal = $state(false);

    // Reactive binding check
    let boundModelName = $derived(data.dbt_model as string | undefined);
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
        isBound ? $dbtModels.find((m) => m.unique_id === boundModelName) : null,
    );

    // Schema editing state for bound models
    let editableColumns = $state<ModelSchemaColumn[]>([]);
    let schemaLoading = $state(false);
    let schemaSaving = $state(false);
    let schemaError = $state<string | null>(null);
    let hasUnsavedChanges = $state(false);

    // Fetch schema when model is bound
    $effect(() => {
        if (isBound && modelDetails) {
            loadSchema();
        } else {
            editableColumns = [];
            hasUnsavedChanges = false;
        }
    });

    async function loadSchema() {
        if (!modelDetails) return;

        schemaLoading = true;
        schemaError = null;

        try {
            const schema = await getModelSchema(modelDetails.name);

            if (schema && schema.columns) {
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

    async function saveSchema() {
        if (!modelDetails) return;

        schemaSaving = true;
        schemaError = null;

        try {
            await updateModelSchema(
                modelDetails.name,
                editableColumns.map((col) => ({
                    name: col.name,
                    data_type: col.data_type,
                    description: col.description,
                })),
                data.description,
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

    function generateSlug(label: string, currentId: string): string {
        // Convert to lowercase and replace spaces/special chars with underscores
        let slug = label
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "_")
            .replace(/^_+|_+$/g, ""); // trim leading/trailing underscores

        // If empty after cleaning, use a default
        if (!slug) slug = "entity";

        // Ensure uniqueness by checking existing node IDs (excluding current node)
        let finalSlug = slug;
        let counter = 1;
        while (
            $nodes.some(
                (node) => node.id === finalSlug && node.id !== currentId,
            )
        ) {
            finalSlug = `${slug}_${counter}`;
            counter++;
        }

        return finalSlug;
    }

    function updateLabel(e: Event) {
        const label = (e.target as HTMLInputElement).value;
        // Just update the label without changing ID (for real-time typing)
        updateNodeData(id, { label });
    }

    function updateIdFromLabel(e: Event) {
        // Called on blur - update the ID based on final label
        const label = (e.target as HTMLInputElement).value;
        const newId = generateSlug(label, id);

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

        // Store the full unique_id (e.g. "model.elmo.entity_booking")
        const updates: Record<string, unknown> = { dbt_model: model.unique_id };
        const hasDescription = (data.description || "").trim().length > 0;
        if (!hasDescription && (model.description || "").trim().length > 0) {
            updates.description = model.description;
        }

        updateNodeData(id, updates);

        // Auto-create relationships from yml relationship tests
        try {
            const inferred = await inferRelationships();

            // Build model name -> entity ID map from current canvas state
            // Include the model we just bound (since data model hasn't saved yet)
            const modelToEntity: Record<string, string> = {};
            for (const node of $nodes) {
                const boundModel =
                    node.id === id ? model.unique_id : node.data?.dbt_model;
                if (boundModel && typeof boundModel === "string") {
                    // Extract model name from "model.project.name" -> "name"
                    const modelName = boundModel.includes(".")
                        ? boundModel.split(".").pop()!
                        : boundModel;
                    modelToEntity[modelName] = node.id;
                }
                // Also map entity ID to itself
                modelToEntity[node.id] = node.id;
            }

            function getParallelOffset(index: number): number {
                if (index === 0) return 0;
                const level = Math.ceil(index / 2);
                const offset = level * 20;
                return index % 2 === 1 ? offset : -offset;
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

                // Check if edge with same field mapping already exists
                const edgeExists = $edges.some(
                    (e) =>
                        ((e.source === sourceEntityId &&
                            e.target === targetEntityId) ||
                            (e.source === targetEntityId &&
                                e.target === sourceEntityId)) &&
                        e.data?.source_field === rel.source_field &&
                        e.data?.target_field === rel.target_field,
                );
                if (edgeExists) continue;

                const existingBetweenPair = $edges.filter(
                    (e) =>
                        (e.source === sourceEntityId &&
                            e.target === targetEntityId) ||
                        (e.source === targetEntityId &&
                            e.target === sourceEntityId),
                ).length;

                // Generate unique edge ID (allow multiple edges between same entities)
                const baseId = `e${sourceEntityId}-${targetEntityId}`;
                let edgeId = baseId;
                let counter = 1;
                while ($edges.some((e) => e.id === edgeId)) {
                    edgeId = `${baseId}-${counter}`;
                    counter++;
                }

                // Create new edge
                const newEdge = {
                    id: edgeId,
                    source: sourceEntityId,
                    target: targetEntityId,
                    type: "custom",
                    data: {
                        label: rel.label || "",
                        type: rel.type || "one_to_many",
                        source_field: rel.source_field,
                        target_field: rel.target_field,
                        parallelOffset: getParallelOffset(existingBetweenPair),
                        label_dx: 0,
                        label_dy: 0,
                    },
                };
                $edges = [...$edges, newEdge];
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

    function toggleCollapse(event: MouseEvent) {
        // Only toggle if clicking on the header background, not on the input
        if ((event.target as HTMLElement).tagName === "INPUT") {
            return;
        }
        updateNodeData(id, { collapsed: !isCollapsed });
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

    function onFieldDrop(targetFieldName: string, e: DragEvent) {
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

        // Create new edge with field mapping (always create new edge to support multiple relationships)
        const newEdge = {
            id: `e${sourceNodeId}-${targetNodeId}-${Date.now()}`,
            source: sourceNodeId,
            target: targetNodeId,
            type: "custom",
            data: {
                label: "",
                type: "one_to_many",
                source_field: $draggingField.fieldName,
                target_field: targetFieldName,
            },
        };
        $edges = [...$edges, newEdge];

        $draggingField = null;
    }
</script>

<div
    class="rounded-lg border bg-white shadow-sm hover:shadow-md relative transition-shadow duration-200"
    class:border-[#26A69A]={selected || isBound}
    class:border-slate-300={!isBound && !selected && !isDragOver}
    class:ring-2={selected || isDragOver}
    class:ring-[#26A69A]={selected}
    class:ring-opacity-50={selected}
    class:ring-blue-200={isDragOver && !selected}
    class:border-blue-500={isDragOver && !selected}
    style={`width:${nodeWidth}px`}
    ondrop={onDrop}
    ondragover={onDragOver}
    ondragenter={onDragEnter}
    ondragleave={onDragLeave}
    role="presentation"
>
    <Handle
        type="target"
        position={Position.Top}
        class="!bg-slate-400 !w-2 !h-2"
    />

    <!-- Header -->
    <div
        class="p-2.5 border-b border-slate-100 bg-slate-50/50 rounded-t-lg flex justify-between items-center cursor-pointer hover:bg-slate-50 transition-colors"
        onclick={toggleCollapse}
        title={isCollapsed ? "Click to expand" : "Click to collapse"}
    >
        <div class="flex items-center gap-2 flex-1 min-w-0">
            <span
                class="text-slate-400 text-[10px] flex-shrink-0 select-none transition-transform duration-200"
            >
                {#if isCollapsed}
                    <Icon icon="lucide:chevron-right" class="w-4 h-4" />
                {:else}
                    <Icon icon="lucide:chevron-down" class="w-4 h-4" />
                {/if}
            </span>
            <input
                value={data.label}
                oninput={updateLabel}
                onblur={updateIdFromLabel}
                onclick={(e) => e.stopPropagation()}
                class="font-bold bg-transparent w-full focus:outline-none focus:bg-white focus:ring-1 focus:ring-[#26A69A] rounded px-1.5 py-0.5 text-sm text-slate-800"
                placeholder="Entity Name"
            />
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
            {#if isBound}
                <div
                    class="w-2 h-2 rounded-full bg-[#26A69A]"
                    title="Bound to {boundModelName}"
                ></div>
            {/if}
            <button
                onclick={handleDeleteClick}
                aria-label="Delete entity {data.label}"
                class="text-slate-400 hover:text-red-600 transition-colors px-1.5 py-0.5 rounded hover:bg-red-50 focus:outline-none focus:ring-1 focus:ring-red-500"
                title="Delete entity"
            >
                <Icon icon="lucide:x" class="w-4 h-4" />
            </button>
        </div>
    </div>

    <!-- Body -->
    {#if !isCollapsed}
        <div class="p-2.5 nodrag">
            {#if $viewMode === "physical" && isBound && modelDetails}
                <div class="text-xs">
                    <div
                        class="font-mono text-slate-500 mb-2.5 bg-slate-50 p-1.5 rounded border border-slate-100 break-all text-[11px]"
                    >
                        {modelDetails.schema}.{modelDetails.table}
                    </div>
                    {#if modelDetails.materialization}
                        <div
                            class="mb-2.5 text-slate-500 flex items-center gap-2"
                        >
                            <span
                                class="font-medium text-[10px] uppercase tracking-wider"
                                >Materialization</span
                            >
                            <span
                                class="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-semibold uppercase border border-slate-200"
                            >
                                {modelDetails.materialization}
                            </span>
                        </div>
                    {/if}

                    {#if modelDetails.tags && modelDetails.tags.length > 0}
                        <div
                            class="mb-2.5 text-slate-500 flex items-center gap-2 flex-wrap"
                        >
                            <span
                                class="font-medium text-[10px] uppercase tracking-wider"
                                >Tags</span
                            >
                            {#each modelDetails.tags as tag}
                                <span
                                    class="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] border border-blue-100"
                                >
                                    {tag}
                                </span>
                            {/each}
                        </div>
                    {/if}

                    {#if schemaLoading}
                        <div
                            class="text-center text-slate-400 py-4 text-[10px] italic"
                        >
                            Loading schema...
                        </div>
                    {:else}
                        <div
                            class="overflow-y-auto border border-slate-200 rounded-md bg-white p-1 scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent nodrag"
                            style={`max-height:${columnPanelHeight}px`}
                        >
                            {#if editableColumns.length > 0}
                                {#each editableColumns as col, index}
                                    <div
                                        class="p-1.5 border-b border-slate-100 last:border-0 bg-white rounded mb-1 relative group hover:bg-slate-50"
                                        class:bg-blue-50={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-2={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-blue-300={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        ondragover={onFieldDragOver}
                                        ondrop={(e) => onFieldDrop(col.name, e)}
                                    >
                                        <div
                                            class="flex gap-1.5 mb-1 items-center"
                                        >
                                            <span
                                                class="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-xs select-none cursor-grab nodrag hover:text-[#26A69A] pt-1"
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
                                                        class="flex-1 px-1.5 py-0.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-[#26A69A] font-medium"
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
                                                        class="w-20 px-1 py-0.5 text-[10px] border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-[#26A69A] uppercase text-slate-600 font-mono"
                                                        placeholder="text"
                                                    />
                                                    <button
                                                        onclick={() =>
                                                            deleteEditableColumn(
                                                                index,
                                                            )}
                                                        class="text-slate-400 hover:text-red-600 p-1 rounded hover:bg-red-50"
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
                                                    class="w-full px-0 text-[10px] text-slate-500 bg-transparent focus:outline-none border-none placeholder:text-slate-300"
                                                    placeholder="Description (optional)"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                {/each}
                            {:else}
                                <div
                                    class="text-center text-slate-400 py-4 text-[10px] italic"
                                >
                                    No columns defined
                                </div>
                            {/if}
                        </div>

                        <button
                            onclick={addEditableColumn}
                            class="mt-2 w-full text-xs text-[#26A69A] hover:bg-teal-50 p-1.5 rounded border border-teal-200 transition-colors font-medium flex items-center justify-center gap-1"
                        >
                            <Icon icon="lucide:plus" class="w-3 h-3" /> Add Column
                        </button>

                        {#if schemaError}
                            <div
                                class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-800 text-[10px]"
                            >
                                {schemaError}
                            </div>
                        {/if}

                        <div class="flex gap-2 mt-2">
                            <button
                                onclick={saveSchema}
                                disabled={!hasUnsavedChanges || schemaSaving}
                                class="flex-1 text-[10px] font-medium p-1.5 rounded border transition-colors flex items-center justify-center gap-1"
                                class:text-[#26A69A]={hasUnsavedChanges &&
                                    !schemaSaving}
                                class:hover:bg-teal-50={hasUnsavedChanges &&
                                    !schemaSaving}
                                class:border-teal-200={hasUnsavedChanges &&
                                    !schemaSaving}
                                class:text-slate-400={!hasUnsavedChanges ||
                                    schemaSaving}
                                class:border-slate-200={!hasUnsavedChanges ||
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
                                class="text-[10px] text-red-500 hover:bg-red-50 p-1.5 rounded border border-red-100 transition-colors font-medium"
                                onclick={unbind}
                            >
                                Unbind
                            </button>
                        </div>
                    {/if}
                </div>
            {:else}
                <!-- When not bound to dbt model: show concept view OR field editor based on view mode -->
                {#if $viewMode === "physical"}
                    <!-- Physical View - Field Editor -->
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

                        <div
                            class="overflow-y-auto border border-slate-200 rounded-md bg-white p-1 scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent nodrag"
                            style={`max-height:${columnPanelHeight}px`}
                        >
                            {#if draftedFields.length > 0}
                                {#each draftedFields as field, index}
                                    <div
                                        class="p-1.5 border-b border-slate-100 last:border-0 bg-white rounded mb-1 relative group hover:bg-slate-50"
                                        class:bg-blue-50={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-2={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        class:ring-blue-300={$draggingField?.nodeId !==
                                            id && $draggingField !== null}
                                        ondragover={onFieldDragOver}
                                        ondrop={(e) =>
                                            onFieldDrop(field.name, e)}
                                    >
                                        <div
                                            class="flex gap-1.5 mb-1 items-center"
                                        >
                                            <span
                                                class="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-xs select-none cursor-grab nodrag hover:text-[#26A69A] pt-1"
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
                                                        class="flex-1 px-1.5 py-0.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-[#26A69A] font-medium"
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
                                                        class="w-20 px-1 py-0.5 text-[10px] border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-[#26A69A] uppercase text-slate-600 font-mono"
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
                                                        class="text-slate-400 hover:text-red-600 p-1 rounded hover:bg-red-50"
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
                                                    class="w-full px-0 text-[10px] text-slate-500 bg-transparent focus:outline-none border-none placeholder:text-slate-300"
                                                    placeholder="Description (optional)"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                {/each}
                            {:else}
                                <div
                                    class="text-center text-slate-400 py-4 text-[10px] italic"
                                >
                                    No fields defined
                                </div>
                            {/if}
                        </div>

                        <button
                            onclick={addDraftedField}
                            class="mt-2 w-full text-xs text-[#26A69A] hover:bg-teal-50 p-1.5 rounded border border-teal-200 transition-colors font-medium flex items-center justify-center gap-1"
                        >
                            <Icon icon="lucide:plus" class="w-3 h-3" /> Add Field
                        </button>
                    </div>
                {:else}
                    <!-- Concept View -->
                    <textarea
                        value={data.description || ""}
                        oninput={updateDescription}
                        class="w-full text-xs text-slate-600 resize-y min-h-[60px] bg-slate-50 focus:outline-none focus:bg-white focus:ring-1 focus:ring-[#26A69A] rounded p-1.5 border border-slate-200"
                        placeholder="Description..."
                    ></textarea>
                    {#if isBound}
                        <div
                            class="mt-2 text-xs text-[#26A69A] flex items-center justify-between bg-teal-50 p-1.5 rounded border border-teal-100"
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
                                class="text-teal-600 hover:text-red-500 ml-1 px-1 transition-colors"
                            >
                                <Icon icon="lucide:x" class="w-3 h-3" />
                            </button>
                        </div>
                    {:else}
                        <div
                            class="mt-2 text-[10px] text-slate-400 text-center border border-dashed border-slate-300 rounded p-3 bg-slate-50 pointer-events-none"
                        >
                            Drag dbt model here
                        </div>
                    {/if}
                {/if}
            {/if}
        </div>
    {/if}

    <Handle
        type="source"
        position={Position.Bottom}
        class="!bg-slate-400 !w-2 !h-2"
    />

    <div
        class="width-resize-handle"
        onpointerdown={(event) => startDimensionResize(event, "width")}
        title="Drag to resize width"
    ></div>

    {#if $viewMode === "physical"}
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
