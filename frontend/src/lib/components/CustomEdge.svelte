<script lang="ts">
  import { 
    BaseEdge, 
    EdgeLabel,
    type EdgeProps,
    useSvelteFlow
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
    data,
    selected
  } = $props<$$Props>();

  const { updateEdge: flowUpdateEdge } = useSvelteFlow();

  // Compute index among parallel edges (edges between same source-target pair)
  const parallelIndex = $derived.by(() => {
    const parallelEdges = $edges.filter(
      (e) => (e.source === source && e.target === target) || (e.source === target && e.target === source)
    );
    return parallelEdges.findIndex((e) => e.id === id);
  });

  const totalParallel = $derived.by(() => {
    return $edges.filter(
      (e) => (e.source === source && e.target === target) || (e.source === target && e.target === source)
    ).length;
  });

  // Calculate base offset for parallel edges - spread them out horizontally
  const baseOffset = $derived.by(() => {
    if (totalParallel <= 1) return 0;
    const spacing = 50; // pixels between parallel edges
    const totalWidth = (totalParallel - 1) * spacing;
    return (parallelIndex * spacing) - (totalWidth / 2);
  });

  // Get stored label offset (user-dragged position)
  let storedOffsetX = $derived((data?.label_dx as number) || 0);
  let storedOffsetY = $derived((data?.label_dy as number) || 0);
  let dragOffsetX = $state(0);
  let dragOffsetY = $state(0);
  let isDraggingLabel = $state(false);
  let dragStartX = 0;
  let dragStartY = 0;

  // Calculate total offset (base parallel + user drag)
  const totalOffsetX = $derived(baseOffset + storedOffsetX + dragOffsetX);
  const totalOffsetY = $derived(storedOffsetY + dragOffsetY);

  // Label position at midpoint plus offsets
  const baseLabelX = $derived((sourceX + targetX) / 2);
  const baseLabelY = $derived((sourceY + targetY) / 2);
  const displayLabelX = $derived(baseLabelX + totalOffsetX);
  const displayLabelY = $derived(baseLabelY + totalOffsetY);

  // Create a custom path: source -> label -> target with straight segments
  const edgePath = $derived.by(() => {
    const labelPosX = displayLabelX;
    const labelPosY = displayLabelY;
    
    // Path goes: source down -> horizontal to label -> down to target level -> to target
    // Using smooth step style with the label as a waypoint
    
    // Determine if we're going left-to-right or right-to-left
    const goingRight = targetX > sourceX;
    const goingDown = targetY > sourceY;
    
    // Calculate intermediate points for step path through label
    const sourceExitY = sourceY + 20; // Exit below source
    const targetEntryY = targetY - 20; // Enter above target
    
    // Build path segments
    let path = `M ${sourceX} ${sourceY}`;
    
    // Go down from source
    path += ` L ${sourceX} ${sourceExitY}`;
    
    // Go horizontal to label X position
    path += ` L ${labelPosX} ${sourceExitY}`;
    
    // Go to label Y position
    path += ` L ${labelPosX} ${labelPosY}`;
    
    // Continue to target entry level
    path += ` L ${labelPosX} ${targetEntryY}`;
    
    // Go horizontal to target X
    path += ` L ${targetX} ${targetEntryY}`;
    
    // Go down to target
    path += ` L ${targetX} ${targetY}`;
    
    return path;
  });

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

  function selectThisEdge() {
    // Deselect all edges and select this one
    $edges = $edges.map(e => ({
      ...e,
      selected: e.id === id
    }));
  }

  function startLabelDrag(e: PointerEvent) {
    // Select this edge when starting to interact with label
    selectThisEdge();
    
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

  // Style overrides for selection
  const edgeStyle = $derived(
    selected 
      ? `stroke: #3b82f6; stroke-width: 2; ${style || ''}` 
      : style
  );
</script>

<BaseEdge path={edgePath} {markerEnd} style={edgeStyle} />

  <EdgeLabel
  x={displayLabelX}
  y={displayLabelY}
>
  <div
    class="pointer-events-auto nodrag nopan bg-white px-2 py-1 rounded shadow border flex flex-col gap-1 min-w-[180px] cursor-move select-none transition-colors"
    class:border-blue-500={selected}
    class:ring-2={selected}
    class:ring-blue-200={selected}
    class:border-gray-200={!selected}
    onpointerdown={startLabelDrag}
    onclick={selectThisEdge}
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
