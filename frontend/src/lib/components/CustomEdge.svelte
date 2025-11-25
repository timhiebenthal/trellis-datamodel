<script lang="ts">
  import { 
    BaseEdge, 
    EdgeLabel,
    getSmoothStepPath,
    type EdgeProps
  } from '@xyflow/svelte';
  import { edges, nodes, viewMode } from '$lib/stores';

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

  let storedOffsetX = $derived((data?.label_dx as number) || 0);
  let storedOffsetY = $derived((data?.label_dy as number) || 0);
  let dragOffsetX = $state(0);
  let dragOffsetY = $state(0);
  let isDraggingLabel = $state(false);
  let dragStartX = 0;
  let dragStartY = 0;

  // Compute index among parallel edges (edges between same source-target pair)
  const parallelIndex = $derived.by(() => {
    const parallelEdges = $edges.filter(
      (e) => (e.source === source && e.target === target) || (e.source === target && e.target === source)
    );
    return parallelEdges.findIndex((e) => e.id === id);
  });

  // Auto-offset for cascading labels (60px vertical spacing)
  const autoCascadeY = $derived(parallelIndex * 70);

  const displayLabelX = $derived(labelX + storedOffsetX + dragOffsetX);
  const displayLabelY = $derived(labelY + storedOffsetY + dragOffsetY + autoCascadeY);

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

  function startLabelDrag(e: PointerEvent) {
    e.stopPropagation();
    e.preventDefault();
    isDraggingLabel = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragOffsetX = 0;
    dragOffsetY = 0;

    const onMove = (moveEvent: PointerEvent) => {
      dragOffsetX = moveEvent.clientX - dragStartX;
      dragOffsetY = moveEvent.clientY - dragStartY;
    };

    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      if (isDraggingLabel) {
        updateEdge({
          label_dx: storedOffsetX + dragOffsetX,
          label_dy: storedOffsetY + dragOffsetY,
        });
      }
      isDraggingLabel = false;
      dragOffsetX = 0;
      dragOffsetY = 0;
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }
</script>

<BaseEdge path={edgePath} {markerEnd} {style} />

  <EdgeLabel
  x={displayLabelX}
  y={displayLabelY}
>
  <div
    class="pointer-events-auto nodrag nopan bg-white px-2 py-1 rounded shadow border border-gray-200 flex flex-col gap-1 min-w-[180px] cursor-move select-none"
    onpointerdown={startLabelDrag}
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
    <!-- Field mappings - only show in Physical view when fields are set -->
    {#if $viewMode === "physical" && (sourceField || targetField)}
    <div class="text-[9px] text-gray-500 text-center border-t border-gray-100 pt-1 mt-1">
      <span class="font-mono"><span class="text-gray-400">{sourceName.toLowerCase()}.</span>{sourceField || '?'}</span>
      <span class="text-gray-400 mx-1">→</span>
      <span class="font-mono"><span class="text-gray-400">{targetName.toLowerCase()}.</span>{targetField || '?'}</span>
    </div>
    {/if}
  </div>
</EdgeLabel>
