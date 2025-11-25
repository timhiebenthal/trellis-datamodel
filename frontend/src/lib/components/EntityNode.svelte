<script lang="ts">
    import {
        Handle,
        Position,
        useSvelteFlow,
        type NodeProps,
    } from "@xyflow/svelte";
    import { viewMode, dbtModels, nodes, edges, draggingField } from "$lib/stores";
    import type { DbtModel, DraftedField, ColumnLink } from "$lib/types";
    import { saveDbtSchema } from "$lib/api";
    import DeleteConfirmModal from "./DeleteConfirmModal.svelte";

    type $$Props = NodeProps;

    let { data, id } = $props<$$Props>();

    const { updateNodeData } = useSvelteFlow();
    let showDeleteModal = $state(false);

    // Reactive binding check
    let boundModelName = $derived(data.dbt_model as string | undefined);
    let isBound = $derived(!!boundModelName);
    let isCollapsed = $derived(data.collapsed ?? false);
    const DEFAULT_WIDTH = 280;
    const DEFAULT_PANEL_HEIGHT = 200;
    const MIN_WIDTH = 220;
    const MAX_WIDTH = 560;
    const MIN_PANEL_HEIGHT = 120;
    const MAX_PANEL_HEIGHT = 480;
    let nodeWidth = $derived(data.width ?? DEFAULT_WIDTH);
    let columnPanelHeight = $derived(data.panelHeight ?? DEFAULT_PANEL_HEIGHT);

    // Find model details by unique_id (e.g. "model.elmo.entity_booking")
    let modelDetails = $derived(
        isBound ? $dbtModels.find((m) => m.unique_id === boundModelName) : null,
    );

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
                if (
                    updatedEdge.source !== edge.source ||
                    updatedEdge.target !== edge.target
                ) {
                    updatedEdge.id = `e${updatedEdge.source}-${updatedEdge.target}`;
                }
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

    function onDrop(event: DragEvent) {
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

            // Clean up fk_link references in other entities that point to this entity
            nodes.update((list) =>
                list.map((node) => {
                    if (node.id === id) return node; // Skip the node being deleted
                    const fields = node.data?.drafted_fields as DraftedField[] | undefined;
                    if (!fields) return node;
                    
                    // Check if any field links to the deleted entity
                    const hasLinkToDeleted = fields.some((f) => f.fk_link?.targetEntity === id);
                    if (!hasLinkToDeleted) return node;
                    
                    // Remove fk_link from fields that reference the deleted entity
                    const updatedFields = fields.map((f) =>
                        f.fk_link?.targetEntity === id ? { ...f, fk_link: undefined } : f
                    );
                    return {
                        ...node,
                        data: { ...node.data, drafted_fields: updatedFields },
                    };
                })
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
    let savingSchema = $state(false);
    let saveSchemaError = $state<string | null>(null);
    
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
    
    function removeLink(index: number) {
        updateDraftedField(index, { fk_link: undefined });
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
    
    function applyFieldLinkToSource(
        sourceNodeId: string,
        fieldName: string,
        targetEntityId: string,
        targetFieldName: string,
    ) {
        const fkLink: ColumnLink = {
            sourceColumn: fieldName,
            targetEntity: targetEntityId,
            targetColumn: targetFieldName,
        };

        if (sourceNodeId === id) {
            const localIndex = draftedFields.findIndex((f) => f.name === fieldName);
            if (localIndex !== -1) {
                updateDraftedField(localIndex, { fk_link: fkLink });
            }
            return;
        }

        nodes.update((list) =>
            list.map((node) => {
                if (node.id !== sourceNodeId) return node;
                const nodeFields = (node.data?.drafted_fields || []) as DraftedField[];
                const hasField = nodeFields.some((f) => f.name === fieldName);
                if (!hasField) return node;

                const updatedFields = nodeFields.map((f) =>
                    f.name === fieldName ? { ...f, fk_link: fkLink } : f,
                );

                return {
                    ...node,
                    data: {
                        ...node.data,
                        drafted_fields: updatedFields,
                    },
                };
            }),
        );
    }
    
    function onFieldDrop(targetFieldName: string, e: DragEvent) {
        e.preventDefault();
        e.stopPropagation(); // Prevent bubble to canvas
        if (!$draggingField || $draggingField.nodeId === id) return;
        
        // Find or create an edge between the two entities
        const sourceNodeId = $draggingField.nodeId;
        const targetNodeId = id;
        
        // Check if edge already exists
        let existingEdge = $edges.find(
            (edge) =>
                (edge.source === sourceNodeId && edge.target === targetNodeId) ||
                (edge.source === targetNodeId && edge.target === sourceNodeId)
        );
        
        if (existingEdge) {
            // Update existing edge with field mapping
            $edges = $edges.map((edge) =>
                edge.id === existingEdge!.id
                    ? {
                          ...edge,
                          data: {
                              ...edge.data,
                              source_field: edge.source === sourceNodeId ? $draggingField!.fieldName : targetFieldName,
                              target_field: edge.target === targetNodeId ? targetFieldName : $draggingField!.fieldName,
                          },
                      }
                    : edge
            );
        } else {
            // Create new edge with field mapping
            const newEdge = {
                id: `e${sourceNodeId}-${targetNodeId}`,
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
        }

        applyFieldLinkToSource(
            sourceNodeId,
            $draggingField.fieldName,
            targetNodeId,
            targetFieldName,
        );
        
        $draggingField = null;
    }

    async function saveToDbtSchema() {
        if (draftedFields.length === 0) {
            saveSchemaError = "No fields to save";
            return;
        }

        // Validate that all fields have names
        const invalidFields = draftedFields.filter((f) => !f.name.trim());
        if (invalidFields.length > 0) {
            saveSchemaError = "All fields must have a name";
            return;
        }
        savingSchema = true;
        saveSchemaError = null;

        try {
            console.log("Saving dbt schema...", {
                id,
                modelName: data.label || id,
                fields: draftedFields,
            });
            const response = await saveDbtSchema(
                id,
                data.label || id,
                draftedFields,
            );
            saveSchemaError = null;
            console.log("Successfully saved dbt schema");
            console.log("File saved to:", response);
            // Show brief success indication
            setTimeout(() => {
                savingSchema = false;
            }, 1000);
        } catch (error) {
            savingSchema = false;
            const errorMessage =
                error instanceof Error
                    ? error.message
                    : "Failed to save schema";
            saveSchemaError = errorMessage;
            console.error("Failed to save dbt schema:", error);
            console.error("Error details:", errorMessage);
        }
    }
</script>

<div
    class="rounded-md border-2 bg-white shadow-sm hover:shadow-md relative"
    class:border-green-500={isBound}
    class:border-blue-500={isDragOver}
    class:border-gray-300={!isBound && !isDragOver}
    class:ring-2={isDragOver}
    class:ring-blue-200={isDragOver}
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
        class="!bg-gray-400 !w-3 !h-3"
    />

    <!-- Header -->
    <div
        class="p-2 border-b border-gray-100 bg-gray-50 rounded-t-md flex justify-between items-center cursor-pointer hover:bg-gray-100 transition-colors"
        onclick={toggleCollapse}
        title={isCollapsed ? "Click to expand" : "Click to collapse"}
    >
        <div class="flex items-center gap-1 flex-1 min-w-0">
            <span
                class="text-gray-500 text-xs flex-shrink-0 select-none transition-transform"
                style={`transform: rotate(${isCollapsed ? 0 : 90}deg)`}
            >
                ▶
            </span>
            <input
                value={data.label}
                oninput={updateLabel}
                onblur={updateIdFromLabel}
                onclick={(e) => e.stopPropagation()}
                class="font-bold bg-transparent w-full focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-300 rounded px-1 text-sm"
                placeholder="Entity Name"
            />
        </div>
        <div class="flex items-center gap-1 flex-shrink-0">
            {#if isBound}
                <div
                    class="w-2 h-2 rounded-full bg-green-500"
                    title="Bound to {boundModelName}"
                ></div>
            {/if}
            <button
                onclick={handleDeleteClick}
                aria-label="Delete entity {data.label}"
                class="text-gray-400 hover:text-red-600 transition-colors px-1 py-0.5 rounded hover:bg-red-50 focus:outline-none focus:ring-1 focus:ring-red-500"
                title="Delete entity"
            >
                ×
            </button>
        </div>
    </div>

    <!-- Body -->
    {#if !isCollapsed}
        <div class="p-2">
            {#if $viewMode === "physical" && isBound && modelDetails}
                <div class="text-xs">
                    <div
                        class="font-mono text-gray-600 mb-2 bg-gray-100 p-1 rounded break-all"
                    >
                        {modelDetails.schema}.{modelDetails.table}
                    </div>
                    {#if modelDetails.materialization}
                        <div class="mb-2 text-gray-500">
                            <span class="font-medium">Materialization:</span>
                            <span
                                class="ml-1 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-semibold uppercase"
                            >
                                {modelDetails.materialization}
                            </span>
                        </div>
                    {/if}
                    <div
                        class="overflow-y-auto border rounded bg-gray-50 p-1 scrollbar-thin"
                        style={`max-height:${columnPanelHeight}px`}
                    >
                        {#each modelDetails.columns as col}
                            <div
                                class="flex justify-between py-1 border-b border-gray-200 last:border-0 group"
                                ondragover={onFieldDragOver}
                                ondrop={(e) => onFieldDrop(col.name, e)}
                                class:bg-blue-50={$draggingField?.nodeId !== id && $draggingField !== null}
                                class:ring-2={$draggingField?.nodeId !== id && $draggingField !== null}
                                class:ring-blue-300={$draggingField?.nodeId !== id && $draggingField !== null}
                            >
                                <span
                                    class="font-medium text-gray-700 truncate pr-2 flex items-center gap-1"
                                    title={col.name}
                                >
                                    <span 
                                        class="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab select-none nodrag"
                                        draggable="true"
                                        onmousedown={(e) => e.stopPropagation()}
                                        onpointerdown={(e) => e.stopPropagation()}
                                        ondragstart={(e) => onFieldDragStart(col.name, e)}
                                        ondragend={onFieldDragEnd}
                                        class:cursor-grabbing={$draggingField?.nodeId === id && $draggingField?.fieldName === col.name}
                                        title="Drag to link to another field"
                                    >⋮⋮</span>
                                    {col.name}
                                </span>
                                <span
                                    class="text-gray-400 text-[10px] uppercase"
                                    >{col.type}</span
                                >
                            </div>
                        {/each}
                    </div>
                    <button
                        class="mt-2 w-full text-xs text-red-500 hover:bg-red-50 p-1 rounded border border-red-100 transition-colors"
                        onclick={unbind}
                    >
                        Unbind Model
                    </button>
                </div>
            {:else}
                <!-- When not bound to dbt model: show concept view OR field editor based on view mode -->
                {#if $viewMode === "physical"}
                    <!-- Physical View - Field Editor -->
                    <div class="text-xs">
                        <div
                            class="mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-800 text-[10px]"
                        >
                            ⚠️ Generic datatypes - may need adjustment for your
                            database
                        </div>

                        <div
                            class="overflow-y-auto border rounded bg-gray-50 p-1 scrollbar-thin"
                            style={`max-height:${columnPanelHeight}px`}
                        >
                            {#if draftedFields.length > 0}
                                {#each draftedFields as field, index}
                                    <div
                                        class="p-2 border-b border-gray-200 last:border-0 bg-white rounded mb-1 relative group"
                                        class:bg-blue-50={$draggingField?.nodeId !== id && $draggingField !== null}
                                        class:ring-2={$draggingField?.nodeId !== id && $draggingField !== null}
                                        class:ring-blue-300={$draggingField?.nodeId !== id && $draggingField !== null}
                                        ondragover={onFieldDragOver}
                                        ondrop={(e) => onFieldDrop(field.name, e)}
                                    >
                                        <div
                                            class="flex gap-1 mb-1 items-center"
                                        >
                                            <span 
                                                class="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity text-xs select-none cursor-grab nodrag"
                                                draggable="true"
                                                onmousedown={(e) => e.stopPropagation()}
                                                onpointerdown={(e) => e.stopPropagation()}
                                                ondragstart={(e) => onFieldDragStart(field.name, e)}
                                                ondragend={onFieldDragEnd}
                                                class:cursor-grabbing={$draggingField?.nodeId === id && $draggingField?.fieldName === field.name}
                                                title="Drag to link to another field"
                                            >⋮⋮</span>
                                            <input
                                                type="text"
                                                value={field.name}
                                                oninput={(e) =>
                                                    updateDraftedField(index, {
                                                        name: (
                                                            e.target as HTMLInputElement
                                                        ).value,
                                                    })}
                                                class="flex-1 px-1 py-0.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                                                placeholder="field_name"
                                            />
                                            <select
                                                value={field.datatype}
                                                onchange={(e) =>
                                                    updateDraftedField(index, {
                                                        datatype: (
                                                            e.target as HTMLSelectElement
                                                        ).value as any,
                                                    })}
                                                class="px-1 py-0.5 text-[10px] border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400 uppercase text-gray-600"
                                            >
                                                <option value="text"
                                                    >text</option
                                                >
                                                <option value="int">int</option>
                                                <option value="float"
                                                    >float</option
                                                >
                                                <option value="bool"
                                                    >bool</option
                                                >
                                                <option value="date"
                                                    >date</option
                                                >
                                                <option value="timestamp"
                                                    >timestamp</option
                                                >
                                            </select>
                                            {#if field.fk_link}
                                                <button
                                                    onclick={() => removeLink(index)}
                                                    class="text-blue-600 hover:text-red-600 px-1"
                                                    title={`Remove link to ${field.fk_link.targetEntity}.${field.fk_link.targetColumn}`}
                                                >
                                                    ✕
                                                </button>
                                            {/if}
                                            <button
                                                onclick={() =>
                                                    deleteDraftedField(index)}
                                                class="text-red-400 hover:text-red-600 px-1"
                                                title="Delete field">×</button
                                            >
                                        </div>
                                        {#if field.fk_link}
                                            <div class="text-[9px] text-blue-600 mb-1">
                                                → {field.fk_link.targetEntity}.{field.fk_link.targetColumn}
                                            </div>
                                        {/if}
                                        <textarea
                                            value={field.description || ""}
                                            oninput={(e) =>
                                                updateDraftedField(index, {
                                                    description: (
                                                        e.target as HTMLTextAreaElement
                                                    ).value,
                                                })}
                                            class="w-full px-1 py-0.5 text-[10px] border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none"
                                            placeholder="Description (optional)"
                                            rows="2"
                                        ></textarea>
                                    </div>
                                {/each}
                            {:else}
                                <div
                                    class="text-center text-gray-400 py-4 text-[10px]"
                                >
                                    No fields defined
                                </div>
                            {/if}
                        </div>

                        <button
                            onclick={addDraftedField}
                            class="mt-2 w-full text-xs text-blue-600 hover:bg-blue-50 p-1 rounded border border-blue-200 transition-colors font-medium"
                        >
                            + Add Field
                        </button>

                        {#if draftedFields.length > 0}
                            <button
                                onclick={saveToDbtSchema}
                                disabled={savingSchema}
                                class="mt-2 w-full text-xs text-green-600 hover:bg-green-50 p-1 rounded border border-green-200 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {savingSchema
                                    ? "✓ Saved!"
                                    : "💾 Save as dbt schema (.yml)"}
                            </button>
                            {#if saveSchemaError}
                                <div
                                    class="mt-1 text-[10px] text-red-600 bg-red-50 p-1 rounded"
                                >
                                    {saveSchemaError}
                                </div>
                            {/if}
                        {/if}
                    </div>
                {:else}
                    <!-- Concept View -->
                    <textarea
                        value={data.description || ""}
                        oninput={updateDescription}
                        class="w-full text-xs text-gray-600 resize-y min-h-[60px] bg-gray-50 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-300 rounded p-1"
                        placeholder="Description..."
                    ></textarea>
                    {#if isBound}
                        <div
                            class="mt-2 text-xs text-green-600 flex items-center justify-between bg-green-50 p-1 rounded border border-green-100"
                        >
                            <span
                                class="truncate font-medium"
                                title={boundModelName}>🔗 {boundModelName}</span
                            >
                            <button
                                onclick={unbind}
                                class="text-red-400 hover:text-red-600 ml-1 px-1"
                                >×</button
                            >
                        </div>
                    {:else}
                        <div
                            class="mt-2 text-[10px] text-gray-400 text-center border border-dashed border-gray-300 rounded p-2 bg-gray-50 pointer-events-none"
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
        class="!bg-gray-400 !w-3 !h-3"
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
        background: rgba(59, 130, 246, 0.3);
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
