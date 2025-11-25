<script lang="ts">
  import { 
    BaseEdge, 
    EdgeLabel,
    getSmoothStepPath,
    type EdgeProps
  } from '@xyflow/svelte';
  import { edges, nodes, dbtModels, viewMode } from '$lib/stores';

  type $$Props = EdgeProps;

  let { 
    id,
    source,
    target,
    sourceX, 
    sourceY, 
    targetX, 
    targetY, 
    sourcePosition, 
    targetPosition,
    style,
    markerEnd,
    data 
  } = $props<$$Props>();

  let [edgePath, labelX, labelY] = $derived(getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition
  }));

  // Use raw data.label for input value, default to empty
  let label = $derived((data?.label as string) || '');
  let type = $derived((data?.type as string) || 'one_to_many');
  let sourceField = $derived((data?.source_field as string) || '');
  let targetField = $derived((data?.target_field as string) || '');
  // Cardinality text map
  const cardinalityText = $derived({
    'one_to_many': 'one → many',
    'many_to_one': 'many → one',
    'one_to_one': 'one → one'
  }[type] || 'one → many');

  const descriptors = $derived(
    {
      one_to_many: { source: 'one', target: 'many' },
      many_to_one: { source: 'many', target: 'one' },
      one_to_one: { source: 'one', target: 'one' }
    }[type] || { source: 'one', target: 'many' }
  );

  const sourceNode = $derived($nodes.find((node) => node.id === source));
  const targetNode = $derived($nodes.find((node) => node.id === target));

  const sourceName = $derived(sourceNode?.data?.label || 'Source');
  const targetName = $derived(targetNode?.data?.label || 'Target');
  const actionText = $derived(label?.trim() || 'relates to');
  
  // Get available columns for source and target entities
  const sourceColumns = $derived.by(() => {
    if (!sourceNode) return [];
    // Check if bound to dbt model
    if (sourceNode.data?.dbt_model) {
      const model = $dbtModels.find(m => m.unique_id === sourceNode.data.dbt_model);
      return model?.columns.map(c => c.name) || [];
    }
    // Check drafted fields
    return (sourceNode.data?.drafted_fields || []).map((f: any) => f.name);
  });
  
  const targetColumns = $derived.by(() => {
    if (!targetNode) return [];
    // Check if bound to dbt model
    if (targetNode.data?.dbt_model) {
      const model = $dbtModels.find(m => m.unique_id === targetNode.data.dbt_model);
      return model?.columns.map(c => c.name) || [];
    }
    // Check drafted fields
    return (targetNode.data?.drafted_fields || []).map((f: any) => f.name);
  });

  const relationText = $derived(
    `${descriptors.source} ${sourceName} ${actionText} ${descriptors.target} ${targetName}`
  );

  function updateEdge(partial: Record<string, unknown>) {
    edges.update((list) =>
      list.map((edge) =>
        edge.id === id
          ? {
              ...edge,
              data: {
                ...(edge.data || {}),
                ...partial
              }
            }
          : edge
      )
    );
  }

  function onLabelChange(e: Event) {
    updateEdge({ label: (e.target as HTMLInputElement).value });
  }

  function toggleType(e: MouseEvent) {
    // Explicitly stop propagation at all levels
    e.stopPropagation();
    e.stopImmediatePropagation();
    
    // Cycle: one_to_many -> many_to_one -> one_to_one -> one_to_many
    let nextType = 'one_to_many';
    if (type === 'one_to_many') nextType = 'many_to_one';
    else if (type === 'many_to_one') nextType = 'one_to_one';
    else nextType = 'one_to_many';
    
    updateEdge({ type: nextType });
  }
</script>

<BaseEdge path={edgePath} {markerEnd} {style} />

<EdgeLabel
  x={labelX}
  y={labelY}
>
  <div
    class="pointer-events-auto nodrag nopan bg-white px-2 py-1 rounded shadow border border-gray-200 flex flex-col gap-1 min-w-[180px]"
    onmousedown={(e) => e.stopPropagation()}
    click={(e) => e.stopPropagation()}
    role="presentation"
  >
    <div class="flex items-center gap-2">
      <input
        value={label}
        oninput={onLabelChange}
        onchange={onLabelChange}
        class="text-xs font-medium focus:outline-none focus:bg-gray-50 flex-1 bg-transparent border border-gray-200 rounded px-1 py-0.5"
        placeholder="relationship..."
      />
      <button 
          class="text-[10px] font-semibold text-gray-600 hover:text-blue-600 hover:bg-gray-100 rounded px-2 py-0.5 cursor-pointer bg-transparent border border-gray-300"
          onclick={toggleType}
          title="Click to toggle type"
          type="button"
      >
          {cardinalityText}
      </button>
    </div>
    <div class="text-[10px] text-gray-500 text-center whitespace-nowrap">
      {relationText}
    </div>
    <!-- Field mappings - only show in Physical view -->
    {#if $viewMode === "physical"}
    <div class="text-[9px] text-gray-400 mt-1 space-y-1">
      <div class="flex items-center gap-1">
        <span class="text-gray-500">From:</span>
        <select
          value={sourceField}
          onchange={(e) => updateEdge({ source_field: (e.target as HTMLSelectElement).value || undefined })}
          class="flex-1 text-[9px] border border-gray-200 rounded px-1 py-0.5 bg-white"
          onclick={(e) => e.stopPropagation()}
        >
          <option value="">Select field...</option>
          {#each sourceColumns as col}
            <option value={col}>{col}</option>
          {/each}
        </select>
      </div>
      <div class="flex items-center gap-1">
        <span class="text-gray-500">To:</span>
        <select
          value={targetField}
          onchange={(e) => updateEdge({ target_field: (e.target as HTMLSelectElement).value || undefined })}
          class="flex-1 text-[9px] border border-gray-200 rounded px-1 py-0.5 bg-white"
          onclick={(e) => e.stopPropagation()}
        >
          <option value="">Select field...</option>
          {#each targetColumns as col}
            <option value={col}>{col}</option>
          {/each}
        </select>
      </div>
    </div>
    {/if}
  </div>
</EdgeLabel>
