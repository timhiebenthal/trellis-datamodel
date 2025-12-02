<script lang="ts">
  import { 
    BaseEdge, 
    EdgeLabel,
    type EdgeProps,
    useSvelteFlow
  } from '@xyflow/svelte';
  import { edges, nodes, viewMode } from '$lib/stores';

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
  }: EdgeProps = $props();

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

  // Get source and target node info for label display
  const sourceNode = $derived($nodes.find(n => n.id === source));
  const targetNode = $derived($nodes.find(n => n.id === target));

  // Determine if edge goes downward (source above target) or upward
  const goesDown = $derived(targetY > sourceY);
  
  // Simple orthogonal edge path using handle positions directly
  // sourceX/Y and targetX/Y are already the handle positions from SvelteFlow
  // The horizontal segment Y position can be adjusted by dragging the label
  const edgePath = $derived.by(() => {
    // Apply parallel edge offset to create spacing between multiple edges
    const offsetSourceX = sourceX + baseOffset;
    const offsetTargetX = targetX + baseOffset;
    
    // Horizontal segment Y - starts at midpoint, can be adjusted by label drag
    const baseMidY = (sourceY + targetY) / 2;
    const adjustedMidY = baseMidY + storedOffsetY + dragOffsetY;
    
    // Step path: vertical from source → horizontal at adjustedMidY → vertical to target
    return `M ${offsetSourceX} ${sourceY} L ${offsetSourceX} ${adjustedMidY} L ${offsetTargetX} ${adjustedMidY} L ${offsetTargetX} ${targetY}`;
  });

  // Label position at the middle of the horizontal segment
  const edgeLabelPos = $derived.by(() => {
    const offsetSourceX = sourceX + baseOffset;
    const offsetTargetX = targetX + baseOffset;
    const baseMidY = (sourceY + targetY) / 2;
    const adjustedMidY = baseMidY + storedOffsetY + dragOffsetY;
    
    // Place label on the horizontal segment
    const labelX = (offsetSourceX + offsetTargetX) / 2 + storedOffsetX + dragOffsetX;
    
    return { x: labelX, y: adjustedMidY };
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

  // sourceNode and targetNode defined above for label names
  const sourceName = $derived((sourceNode?.data?.label as string) || 'Source');
  const targetName = $derived((targetNode?.data?.label as string) || 'Target');
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
  
  // Crow's foot marker positions - at the handle positions (sourceX/Y and targetX/Y)
  // Apply the same parallel edge offset
  const sourceMarkerX = $derived(sourceX + baseOffset);
  const targetMarkerX = $derived(targetX + baseOffset);
  const markerColor = $derived(selected ? '#26A69A' : '#64748b');

  // Markers orientation depends on edge direction:
  // - If edge goes DOWN (source above target): source marker points down (180°), target points up (0°)
  // - If edge goes UP (source below target): source marker points up (0°), target points down (180°)
  const sourceMarkerRotation = $derived(goesDown ? 180 : 0);
  const targetMarkerRotation = $derived(goesDown ? 0 : 180);
  
  const sourceMarkerTransform = $derived(
    `translate(${sourceMarkerX} ${sourceY}) rotate(${sourceMarkerRotation})`,
  );
  const targetMarkerTransform = $derived(
    `translate(${targetMarkerX} ${targetY}) rotate(${targetMarkerRotation})`,
  );
</script>

<BaseEdge path={edgePath} {markerEnd} style={edgeStyle} />

<!-- Crow's foot notation markers - on VERTICAL segments near entities -->
<!-- Crow's foot points AT the entity box, zero circle toward the middle of the edge -->
<g class="crow-foot-markers">
  <g transform={sourceMarkerTransform}>
    {#if descriptors.source === 'one'}
      <line x1="-6" y1="-2" x2="6" y2="-2" stroke={markerColor} stroke-width="2" />
    {:else if descriptors.source === 'zero_or_one'}
      <line x1="-6" y1="-4" x2="6" y2="-4" stroke={markerColor} stroke-width="2" />
      <circle cx="0" cy="6" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
    {:else if descriptors.source === 'zero_or_many'}
      <line x1="0" y1="2" x2="-5" y2="-6" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="2" x2="0" y2="-6" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="2" x2="5" y2="-6" stroke={markerColor} stroke-width="1.5" />
      <circle cx="0" cy="10" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
    {:else}
      <line x1="0" y1="4" x2="-5" y2="-5" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="4" x2="0" y2="-5" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="4" x2="5" y2="-5" stroke={markerColor} stroke-width="1.5" />
    {/if}
  </g>

  <g transform={targetMarkerTransform}>
    {#if descriptors.target === 'one'}
      <line x1="-6" y1="-2" x2="6" y2="-2" stroke={markerColor} stroke-width="2" />
    {:else if descriptors.target === 'zero_or_one'}
      <circle cx="0" cy="-6" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
      <line x1="-6" y1="4" x2="6" y2="4" stroke={markerColor} stroke-width="2" />
    {:else if descriptors.target === 'zero_or_many'}
      <circle cx="0" cy="-10" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="-5" y2="6" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="0" y2="6" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="5" y2="6" stroke={markerColor} stroke-width="1.5" />
    {:else}
      <line x1="0" y1="-4" x2="-5" y2="5" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-4" x2="0" y2="5" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-4" x2="5" y2="5" stroke={markerColor} stroke-width="1.5" />
    {/if}
  </g>
</g>

{#if selected}
  <!-- Expanded view when selected - use EdgeLabel for proper positioning -->
  <EdgeLabel x={edgeLabelPos.x} y={edgeLabelPos.y} style="background: transparent;">
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
    style="cursor: pointer; pointer-events: all;"
  >
    <!-- Background rectangle to mask the edge line - matches canvas bg -->
    <rect
      x={edgeLabelPos.x - (displayLabel.length * 3.5) - 8}
      y={edgeLabelPos.y - 10}
      width={displayLabel.length * 7 + 16}
      height="20"
      fill="#f8fafc"
      stroke="#e2e8f0"
      stroke-width="1"
      rx="4"
      ry="4"
    />
    <text
      x={edgeLabelPos.x}
      y={edgeLabelPos.y}
      text-anchor="middle"
      dominant-baseline="middle"
      class="pointer-events-none"
      fill="#64748b"
      font-size="11"
      font-weight="500"
    >
      {displayLabel}
    </text>
  </g>
{/if}
