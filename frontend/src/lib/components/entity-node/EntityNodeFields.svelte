<script lang="ts">
    import Icon from "@iconify/svelte";
    import { draggingField } from "$lib/stores";
    import type { DbtColumn, DraftedField } from "$lib/types";
    import { mergeFields } from "$lib/utils/merged-fields";
    import { formatModelHint, type FrameworkCopy } from "$lib/utils/framework-display";
    import {
        appendDraftedField,
        removeDraftedFieldAt,
        updateDraftedFieldAt,
    } from "$lib/utils/drafted-fields";
    import { createFieldDragDrop } from "$lib/services/field-drag-drop";

    let {
        id,
        nodeLabel,
        columns,
        draftedFields,
        columnPanelHeight,
        frameworkCopy,
        modelName,
        onDraftedFieldsChange,
    }: {
        id: string;
        /** Label recorded on the drag state (falls back to the id). */
        nodeLabel: string;
        /** Columns of the active bound model, if any. */
        columns: DbtColumn[] | undefined;
        draftedFields: DraftedField[];
        columnPanelHeight: number;
        frameworkCopy: FrameworkCopy;
        modelName: string | undefined;
        onDraftedFieldsChange: (fields: DraftedField[]) => void;
    } = $props();

    let mergedFields = $derived(mergeFields(columns, draftedFields));

    const { onFieldDragStart, onFieldDragEnd, onFieldDragOver, onFieldDrop } =
        createFieldDragDrop(() => id, () => nodeLabel);

    function addDraftedField() {
        onDraftedFieldsChange(appendDraftedField(draftedFields));
    }

    function updateDraftedField(index: number, updates: Partial<DraftedField>) {
        onDraftedFieldsChange(updateDraftedFieldAt(draftedFields, index, updates));
    }

    function deleteDraftedField(index: number) {
        onDraftedFieldsChange(removeDraftedFieldAt(draftedFields, index));
    }
</script>

<div
    class="overflow-y-auto border border-gray-200 rounded-md bg-white p-1 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent nodrag"
    style={`max-height:${columnPanelHeight}px`}
>
    {#if mergedFields.length > 0}
        {#each mergedFields as field (field.name)}
            <div
                class="p-1.5 border-b border-gray-100 last:border-0 bg-white rounded mb-1 relative group hover:bg-gray-50"
                class:bg-blue-50={$draggingField?.nodeId !==
                    id && $draggingField !== null}
                class:ring-2={$draggingField?.nodeId !==
                    id && $draggingField !== null}
                class:ring-blue-300={$draggingField?.nodeId !==
                    id && $draggingField !== null}
                ondragover={onFieldDragOver}
                ondrop={(e) => onFieldDrop(field.name, e)}
                role="presentation"
            >
                <div
                    class="flex gap-1.5 mb-1 items-center"
                >
                    <!-- Origin indicator -->
                    <span
                        class="inline-block h-2 w-2 rounded-full border border-primary-500 flex-shrink-0"
                        class:bg-primary-500={field.origin === 'dbt'}
                        data-origin={field.origin}
                        aria-label={field.origin === 'dbt'
                            ? formatModelHint(frameworkCopy.materializedHint, modelName ?? '')
                            : formatModelHint(frameworkCopy.unmaterializedHint, modelName ?? '')}
                        title={field.origin === 'dbt'
                            ? formatModelHint(frameworkCopy.materializedHint, modelName ?? '')
                            : formatModelHint(frameworkCopy.unmaterializedHint, modelName ?? '')}
                        role="img"
                    ></span>

                    {#if field.origin === 'dbt'}
                        <!-- Read-only row for dbt-sourced columns -->
                        <span
                            class="text-gray-400 text-xs select-none w-3 h-3"
                            draggable="true"
                            ondragstart={(e) => onFieldDragStart(field.name, e)}
                            ondragend={onFieldDragEnd}
                            role="presentation"
                            aria-hidden="true"
                            tabindex="-1"
                        >
                            <Icon icon="lucide:link" class="w-3 h-3" />
                        </span>
                        <div class="flex-1 flex flex-col gap-1">
                            <div class="flex items-center gap-1">
                                <span class="flex-1 px-1.5 py-0.5 text-xs font-medium text-gray-700">{field.name}</span>
                                <span class="w-20 px-1 py-0.5 text-[10px] uppercase text-gray-500 font-mono">{field.datatype ?? '—'}</span>
                            </div>
                            {#if field.description}
                                <span class="w-full px-0 text-[10px] text-gray-400">{field.description}</span>
                            {/if}
                        </div>
                    {:else}
                        <!-- Editable row for drafted fields -->
                        <span
                            class="text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity text-xs select-none cursor-grab nodrag hover:text-primary-500 pt-1"
                            draggable="true"
                            onmousedown={(e) => e.stopPropagation()}
                            onpointerdown={(e) => e.stopPropagation()}
                            ondragstart={(e) => onFieldDragStart(field.name, e)}
                            ondragend={onFieldDragEnd}
                            class:cursor-grabbing={$draggingField?.nodeId === id &&
                                $draggingField?.fieldName === field.name}
                            title="Drag to link to another field"
                            role="presentation"
                            aria-hidden="true"
                            tabindex="-1"
                        >
                            <Icon icon="lucide:link" class="w-3 h-3" />
                        </span>
                        <div class="flex-1 flex flex-col gap-1">
                            <div class="flex items-center gap-1">
                                <input
                                    type="text"
                                    value={field.name}
                                    oninput={(e) =>
                                        updateDraftedField(
                                            field.draftIndex,
                                            {
                                                name: (e.target as HTMLInputElement).value,
                                            },
                                        )}
                                    class="flex-1 inline-input px-1.5 py-0.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary-500 font-medium"
                                    placeholder="field_name"
                                />
                                <select
                                    value={field.datatype}
                                    onchange={(e) =>
                                        updateDraftedField(
                                            field.draftIndex,
                                            {
                                                datatype: (e.target as HTMLSelectElement).value as DraftedField['datatype'],
                                            },
                                        )}
                                    class="w-20 px-1 py-0.5 text-[10px] border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 uppercase text-gray-600 font-mono"
                                >
                                    <option value="text">text</option>
                                    <option value="int">int</option>
                                    <option value="float">float</option>
                                    <option value="bool">bool</option>
                                    <option value="date">date</option>
                                    <option value="timestamp">timestamp</option>
                                </select>
                                <button
                                    onclick={() => deleteDraftedField(field.draftIndex)}
                                    class="text-gray-400 hover:text-danger-600 p-1 rounded hover:bg-danger-50"
                                    title="Delete field"
                                >
                                    <Icon icon="lucide:x" class="w-3 h-3" />
                                </button>
                            </div>
                            <input
                                type="text"
                                value={field.description ?? ''}
                                oninput={(e) =>
                                    updateDraftedField(
                                        field.draftIndex,
                                        {
                                            description: (e.target as HTMLInputElement).value,
                                        },
                                    )}
                                class="w-full px-0 text-[10px] text-gray-500 bg-transparent focus:outline-none border-none placeholder:text-gray-300"
                                placeholder="Description (optional)"
                            />
                        </div>
                    {/if}
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
