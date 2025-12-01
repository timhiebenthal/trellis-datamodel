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
  
  // Display text for collapsed state - show label or placeholder
  const displayLabel = $derived(label?.trim() || 'relates to');
  
  // All relationship types with their display text and cardinality descriptors
  // Format: source_cardinality_to_target_cardinality
  // Cardinalities: one (exactly one), zero_or_one (0..1), many (1..*), zero_or_many (0..*)
  const relationshipTypes = {
    'one_to_one':           { text: '1 → 1',    source: 'one',         target: 'one' },
    'one_to_many':          { text: '1 → *',    source: 'one',         target: 'many' },
    'one_to_zero_or_one':   { text: '1 → 0..1', source: 'one',         target: 'zero_or_one' },
    'one_to_zero_or_many':  { text: '1 → 0..*', source: 'one',         target: 'zero_or_many' },
    'many_to_one':          { text: '* → 1',    source: 'many',        target: 'one' },
    'many_to_many':         { text: '* → *',    source: 'many',        target: 'many' },
    'zero_or_one_to_one':   { text: '0..1 → 1', source: 'zero_or_one', target: 'one' },
    'zero_or_one_to_many':  { text: '0..1 → *', source: 'zero_or_one', target: 'many' },
    'zero_or_many_to_one':  { text: '0..* → 1', source: 'zero_or_many', target: 'one' },
    'zero_or_many_to_many': { text: '0..* → *', source: 'zero_or_many', target: 'many' },
  } as const;
  
  // Order for cycling through types
  const typeOrder = [
    'one_to_many',
    'many_to_one', 
    'one_to_one',
    'one_to_zero_or_many',
    'zero_or_one_to_many',
    'zero_or_many_to_one',
    'many_to_many',
  ];
  
  // Cardinality text map
  const cardinalityText = $derived(
    relationshipTypes[type as keyof typeof relationshipTypes]?.text || '1 → *'
  );

  const descriptors = $derived(
    relationshipTypes[type as keyof typeof relationshipTypes] || { source: 'one', target: 'many' }
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
    
    // Cycle through relationship types
    const currentIndex = typeOrder.indexOf(type);
    const nextIndex = (currentIndex + 1) % typeOrder.length;
    const nextType = typeOrder[nextIndex];
    
    updateEdge({ type: nextType });
  }

  function selectThisEdge(e: MouseEvent) {
    e.stopPropagation();
    // Deselect all edges and select this one
    $edges = $edges.map(edge => ({
      ...edge,
      selected: edge.id === id
    }));
  }
  
  function deselectEdge() {
    // Deselect this edge when clicking outside
    $edges = $edges.map(edge => ({
      ...edge,
      selected: edge.id === id ? false : edge.selected
    }));
  }

  function startLabelDrag(e: PointerEvent) {
    // Select this edge when starting to interact with label
    selectThisEdge(e as unknown as MouseEvent);

    const targetEl = e.target as HTMLElement | null;
    const isInteractive = targetEl?.closest('input,button,textarea,select,[contenteditable="true"]');
    if (isInteractive) {
      // Allow form controls to receive focus/typing but keep the event local
      e.stopPropagation();
      return;
    }
    
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

  // Style overrides for selection - Use #26A69A (Teal)
  const edgeStyle = $derived(
    selected 
      ? `stroke: #26A69A; stroke-width: 2; ${style || ''}` 
      : style
  );
  
  // Crow's foot marker positions - directly at the entity box connection points
  // Source marker: right at the bottom of the source box
  const sourceMarkerX = $derived(sourceX);
  const sourceMarkerY = $derived(sourceY + 2);
  
  // Target marker: right at the top of the target box
  const targetMarkerX = $derived(targetX);
  const targetMarkerY = $derived(targetY - 2);
</script>

<BaseEdge path={edgePath} {markerEnd} style={edgeStyle} />

<!-- Crow's foot notation markers - on VERTICAL segments near entities -->
<!-- Crow's foot points AT the entity box, zero circle toward the middle of the edge -->
<g class="crow-foot-markers">
  <!-- Source marker - on vertical segment, crow's foot points UP toward source box -->
  {#if descriptors.source === 'one'}
    <!-- One: horizontal line crossing vertical edge -->
    <line 
      x1={sourceMarkerX - 5} y1={sourceMarkerY} 
      x2={sourceMarkerX + 5} y2={sourceMarkerY}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="2"
    />
  {:else if descriptors.source === 'zero_or_one'}
    <!-- Zero or One: horizontal line (toward box) + circle below (toward middle) -->
    <line 
      x1={sourceMarkerX - 5} y1={sourceMarkerY - 4} 
      x2={sourceMarkerX + 5} y2={sourceMarkerY - 4}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="2"
    />
    <circle 
      cx={sourceMarkerX} cy={sourceMarkerY + 6}
      r="4"
      fill="none"
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
  {:else if descriptors.source === 'zero_or_many'}
    <!-- Zero or Many: crow's foot pointing UP + circle below -->
    <line 
      x1={sourceMarkerX} y1={sourceMarkerY + 2} 
      x2={sourceMarkerX - 5} y2={sourceMarkerY - 6}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={sourceMarkerX} y1={sourceMarkerY + 2} 
      x2={sourceMarkerX} y2={sourceMarkerY - 6}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={sourceMarkerX} y1={sourceMarkerY + 2} 
      x2={sourceMarkerX + 5} y2={sourceMarkerY - 6}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <circle 
      cx={sourceMarkerX} cy={sourceMarkerY + 10}
      r="4"
      fill="none"
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
  {:else}
    <!-- Many: crow's foot pointing UP toward source box -->
    <line 
      x1={sourceMarkerX} y1={sourceMarkerY + 4} 
      x2={sourceMarkerX - 5} y2={sourceMarkerY - 5}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={sourceMarkerX} y1={sourceMarkerY + 4} 
      x2={sourceMarkerX} y2={sourceMarkerY - 5}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={sourceMarkerX} y1={sourceMarkerY + 4} 
      x2={sourceMarkerX + 5} y2={sourceMarkerY - 5}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
  {/if}
  
  <!-- Target marker - on vertical segment, crow's foot points DOWN toward target box -->
  {#if descriptors.target === 'one'}
    <!-- One: horizontal line crossing vertical edge -->
    <line 
      x1={targetMarkerX - 5} y1={targetMarkerY} 
      x2={targetMarkerX + 5} y2={targetMarkerY}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="2"
    />
  {:else if descriptors.target === 'zero_or_one'}
    <!-- Zero or One: circle above (toward middle) + horizontal line below (toward box) -->
    <circle 
      cx={targetMarkerX} cy={targetMarkerY - 6}
      r="4"
      fill="none"
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={targetMarkerX - 5} y1={targetMarkerY + 4} 
      x2={targetMarkerX + 5} y2={targetMarkerY + 4}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="2"
    />
  {:else if descriptors.target === 'zero_or_many'}
    <!-- Zero or Many: circle above + crow's foot pointing DOWN -->
    <circle 
      cx={targetMarkerX} cy={targetMarkerY - 10}
      r="4"
      fill="none"
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={targetMarkerX} y1={targetMarkerY - 2} 
      x2={targetMarkerX - 5} y2={targetMarkerY + 6}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={targetMarkerX} y1={targetMarkerY - 2} 
      x2={targetMarkerX} y2={targetMarkerY + 6}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={targetMarkerX} y1={targetMarkerY - 2} 
      x2={targetMarkerX + 5} y2={targetMarkerY + 6}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
  {:else}
    <!-- Many: crow's foot pointing DOWN toward target box -->
    <line 
      x1={targetMarkerX} y1={targetMarkerY - 4} 
      x2={targetMarkerX - 5} y2={targetMarkerY + 5}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={targetMarkerX} y1={targetMarkerY - 4} 
      x2={targetMarkerX} y2={targetMarkerY + 5}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
    <line 
      x1={targetMarkerX} y1={targetMarkerY - 4} 
      x2={targetMarkerX + 5} y2={targetMarkerY + 5}
      stroke={selected ? '#26A69A' : '#64748b'}
      stroke-width="1.5"
    />
  {/if}
</g>

{#if selected}
  <!-- Expanded view when selected - use EdgeLabel for proper positioning -->
  <EdgeLabel x={displayLabelX} y={displayLabelY} style="background: transparent;">
    <div
      class="pointer-events-auto nodrag nopan bg-slate-50 px-2.5 py-2 rounded-lg shadow-lg border-2 border-[#26A69A] flex flex-col gap-1.5 cursor-move select-none transition-all duration-150"
      style="background: rgb(248 250 252);"
      onpointerdown={startLabelDrag}
      role="presentation"
    >
      <div class="flex items-center gap-2">
        <input
          value={label}
          oninput={onLabelChange}
          onchange={onLabelChange}
          class="text-xs font-medium focus:outline-none bg-white flex-1 border border-slate-200 rounded px-1.5 py-0.5 focus:border-[#26A69A] min-w-[100px]"
          placeholder="relationship..."
        />
        <button 
            class="text-[10px] font-semibold text-slate-600 hover:text-[#26A69A] hover:bg-white rounded px-2 py-0.5 cursor-pointer bg-slate-100 border border-slate-300 whitespace-nowrap"
            onclick={toggleType}
            title="Click to toggle type"
            type="button"
        >
            {cardinalityText}
        </button>
      </div>
      <div class="text-[10px] text-slate-500 text-center whitespace-nowrap">
        {relationText}
      </div>
      <!-- Field mappings - only show in Logical view when fields are set -->
      {#if $viewMode === "logical" && (sourceField || targetField)}
      <div class="text-[9px] text-slate-500 text-center border-t border-slate-200 pt-1 mt-0.5">
        <span class="font-mono"><span class="text-slate-400">{sourceName.toLowerCase()}.</span>{sourceField || '?'}</span>
        <span class="text-slate-400 mx-1">→</span>
        <span class="font-mono"><span class="text-slate-400">{targetName.toLowerCase()}.</span>{targetField || '?'}</span>
      </div>
      {/if}
    </div>
  </EdgeLabel>
{:else}
  <!-- Compact text-only view - SVG text with background to mask edge line -->
  <g 
    class="edge-label-compact"
    onclick={selectThisEdge}
    onpointerdown={(e) => { e.stopPropagation(); startLabelDrag(e); }}
    style="cursor: pointer;"
  >
    <!-- Background rectangle to mask the edge line - matches canvas bg -->
    <rect
      x={displayLabelX - (displayLabel.length * 3.5) - 6}
      y={displayLabelY - 9}
      width={displayLabel.length * 7 + 12}
      height="18"
      fill="#f8fafc"
      rx="9"
      ry="9"
    />
    <text
      x={displayLabelX}
      y={displayLabelY}
      text-anchor="middle"
      dominant-baseline="middle"
      class="pointer-events-auto"
      fill="#64748b"
      font-size="11"
      font-weight="500"
    >
      {displayLabel}
    </text>
  </g>
{/if}
