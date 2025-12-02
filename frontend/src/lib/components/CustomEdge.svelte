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

  // Get source and target node info
  const sourceNode = $derived($nodes.find(n => n.id === source));
  const targetNode = $derived($nodes.find(n => n.id === target));

  // Helper to get node dimensions - prefer SvelteFlow's measured dimensions
  function getNodeDimensions(node: any): { width: number; height: number } {
    // Use SvelteFlow's measured dimensions if available (most accurate)
    if (node?.measured?.width && node?.measured?.height) {
      return { width: node.measured.width, height: node.measured.height };
    }
    
    // Fallback to data dimensions matching EntityNode.svelte defaults
    const DEFAULT_WIDTH = 320;
    if (!node) return { width: DEFAULT_WIDTH, height: 200 };
    
    const width = (node.data?.width as number) || DEFAULT_WIDTH;
    const panelHeight = (node.data?.panelHeight as number) || 200;
    const collapsed = node.data?.collapsed ?? false;
    
    // Collapsed height: header (~40px)
    // Expanded height: header + panel + tags + padding (~100px overhead)
    const height = collapsed ? 40 : panelHeight + 100;
    return { width, height };
  }

  // Helper to get absolute node position (accounting for parent groups)
  function getNodeAbsolutePosition(node: any): { x: number; y: number } {
    if (!node) return { x: 0, y: 0 };
    
    // Use SvelteFlow's positionAbsolute if available (handles nested nodes)
    if (node.computed?.positionAbsolute) {
      return { x: node.computed.positionAbsolute.x, y: node.computed.positionAbsolute.y };
    }
    if (node.positionAbsolute) {
      return { x: node.positionAbsolute.x, y: node.positionAbsolute.y };
    }
    
    // Fallback: manually calculate from position + parent offset
    let x = node.position?.x ?? 0;
    let y = node.position?.y ?? 0;
    
    if (node.parentId) {
      const parent = $nodes.find(n => n.id === node.parentId);
      if (parent) {
        const parentPos = getNodeAbsolutePosition(parent);
        x += parentPos.x;
        y += parentPos.y;
      }
    }
    return { x, y };
  }

  // Helper to get absolute node center
  function getNodeCenter(node: any): { x: number; y: number } {
    const pos = getNodeAbsolutePosition(node);
    const dim = getNodeDimensions(node);
    return {
      x: pos.x + dim.width / 2,
      y: pos.y + dim.height / 2
    };
  }

  type Side = 'top' | 'bottom' | 'left' | 'right';

  // Calculate optimal connection points on closest sides
  const connectionInfo = $derived.by(() => {
    const sourceCenter = getNodeCenter(sourceNode);
    const targetCenter = getNodeCenter(targetNode);
    const sourceDim = getNodeDimensions(sourceNode);
    const targetDim = getNodeDimensions(targetNode);
    
    const dx = targetCenter.x - sourceCenter.x;
    const dy = targetCenter.y - sourceCenter.y;
    
    let sourceSide: Side;
    let targetSide: Side;
    let sourcePoint: { x: number; y: number };
    let targetPoint: { x: number; y: number };
    
    // Choose sides based on relative positions - pick closest pair
    if (Math.abs(dx) > Math.abs(dy)) {
      // Horizontal arrangement - use left/right sides
      if (dx > 0) {
        sourceSide = 'right';
        targetSide = 'left';
        sourcePoint = { x: sourceCenter.x + sourceDim.width / 2, y: sourceCenter.y };
        targetPoint = { x: targetCenter.x - targetDim.width / 2, y: targetCenter.y };
      } else {
        sourceSide = 'left';
        targetSide = 'right';
        sourcePoint = { x: sourceCenter.x - sourceDim.width / 2, y: sourceCenter.y };
        targetPoint = { x: targetCenter.x + targetDim.width / 2, y: targetCenter.y };
      }
    } else {
      // Vertical arrangement - use top/bottom sides
      if (dy > 0) {
        sourceSide = 'bottom';
        targetSide = 'top';
        sourcePoint = { x: sourceCenter.x, y: sourceCenter.y + sourceDim.height / 2 };
        targetPoint = { x: targetCenter.x, y: targetCenter.y - targetDim.height / 2 };
      } else {
        sourceSide = 'top';
        targetSide = 'bottom';
        sourcePoint = { x: sourceCenter.x, y: sourceCenter.y - sourceDim.height / 2 };
        targetPoint = { x: targetCenter.x, y: targetCenter.y + targetDim.height / 2 };
      }
    }
    
    return { sourceSide, targetSide, sourcePoint, targetPoint };
  });

  // Build orthogonal edge path based on connection sides
  const edgePath = $derived.by(() => {
    const { sourceSide, targetSide, sourcePoint, targetPoint } = connectionInfo;
    
    let sX = sourcePoint.x;
    let sY = sourcePoint.y;
    let tX = targetPoint.x;
    let tY = targetPoint.y;
    
    // Apply parallel edge offset perpendicular to exit direction
    if (sourceSide === 'left' || sourceSide === 'right') {
      sY += baseOffset;
      tY += baseOffset;
    } else {
      sX += baseOffset;
      tX += baseOffset;
    }
    
    // Route based on connection configuration
    if (sourceSide === 'right' && targetSide === 'left') {
      // Horizontal: right → left
      const midX = (sX + tX) / 2 + storedOffsetX + dragOffsetX;
      return `M ${sX} ${sY} L ${midX} ${sY} L ${midX} ${tY} L ${tX} ${tY}`;
    } else if (sourceSide === 'left' && targetSide === 'right') {
      // Horizontal: left → right
      const midX = (sX + tX) / 2 + storedOffsetX + dragOffsetX;
      return `M ${sX} ${sY} L ${midX} ${sY} L ${midX} ${tY} L ${tX} ${tY}`;
    } else if (sourceSide === 'bottom' && targetSide === 'top') {
      // Vertical: down → up
      const midY = (sY + tY) / 2 + storedOffsetY + dragOffsetY;
      return `M ${sX} ${sY} L ${sX} ${midY} L ${tX} ${midY} L ${tX} ${tY}`;
    } else {
      // Vertical: up → down
      const midY = (sY + tY) / 2 + storedOffsetY + dragOffsetY;
      return `M ${sX} ${sY} L ${sX} ${midY} L ${tX} ${midY} L ${tX} ${tY}`;
    }
  });

  // Label position at the middle of the edge
  const edgeLabelPos = $derived.by(() => {
    const { sourceSide, sourcePoint, targetPoint } = connectionInfo;
    
    let sX = sourcePoint.x;
    let sY = sourcePoint.y;
    let tX = targetPoint.x;
    let tY = targetPoint.y;
    
    if (sourceSide === 'left' || sourceSide === 'right') {
      sY += baseOffset;
      tY += baseOffset;
      const midX = (sX + tX) / 2 + storedOffsetX + dragOffsetX;
      const midY = (sY + tY) / 2;
      return { x: midX, y: midY };
    } else {
      sX += baseOffset;
      tX += baseOffset;
      const midX = (sX + tX) / 2;
      const midY = (sY + tY) / 2 + storedOffsetY + dragOffsetY;
      return { x: midX, y: midY };
    }
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
  
  // Crow's foot marker positions and rotations based on connection sides
  const markerColor = $derived(selected ? '#26A69A' : '#64748b');

  // Get rotation angle based on connection side
  // Crow's feet always point TOWARD the node (per standard ERD notation)
  // Reference: https://github.com/relliv/crows-foot-notations
  // Markers are drawn with trident at negative Y (pointing UP at 0°)
  // The side indicates which side of the NODE the connection is on
  // - bottom: connection at bottom of node → marker points UP toward node → 0°
  // - top: connection at top of node → marker points DOWN toward node → 180°
  // - left: connection at left of node → marker points RIGHT toward node → 90°
  // - right: connection at right of node → marker points LEFT toward node → -90°
  function getSideRotation(side: Side): number {
    switch (side) {
      case 'bottom': return 0;    // Marker points UP (toward node above)
      case 'top': return 180;     // Marker points DOWN (toward node below)
      case 'left': return 90;     // Marker points RIGHT (toward node on right)
      case 'right': return -90;   // Marker points LEFT (toward node on left)
    }
  }

  // Padding to offset markers slightly away from node border
  const MARKER_PADDING = 8;

  const sourceMarkerTransform = $derived.by(() => {
    const { sourceSide, sourcePoint } = connectionInfo;
    let x = sourcePoint.x;
    let y = sourcePoint.y;
    
    // Apply parallel edge offset
    if (sourceSide === 'left' || sourceSide === 'right') {
      y += baseOffset;
    } else {
      x += baseOffset;
    }
    
    // Apply padding away from node border
    switch (sourceSide) {
      case 'top': y -= MARKER_PADDING; break;
      case 'bottom': y += MARKER_PADDING; break;
      case 'left': x -= MARKER_PADDING; break;
      case 'right': x += MARKER_PADDING; break;
    }
    
    return `translate(${x} ${y}) rotate(${getSideRotation(sourceSide)})`;
  });

  const targetMarkerTransform = $derived.by(() => {
    const { targetSide, targetPoint } = connectionInfo;
    let x = targetPoint.x;
    let y = targetPoint.y;
    
    // Apply parallel edge offset
    if (targetSide === 'left' || targetSide === 'right') {
      y += baseOffset;
    } else {
      x += baseOffset;
    }
    
    // Apply padding away from node border
    switch (targetSide) {
      case 'top': y -= MARKER_PADDING; break;
      case 'bottom': y += MARKER_PADDING; break;
      case 'left': x -= MARKER_PADDING; break;
      case 'right': x += MARKER_PADDING; break;
    }
    
    return `translate(${x} ${y}) rotate(${getSideRotation(targetSide)})`;
  });
</script>

<BaseEdge path={edgePath} {markerEnd} style={edgeStyle} />

<!-- Crow's foot notation markers - on VERTICAL segments near entities -->
<!-- Crow's foot points AT the entity box, zero circle toward the middle of the edge -->
<g class="crow-foot-markers">
  <!-- Source marker: trident points TOWARD node (negative Y), circle AWAY (positive Y = toward edge) -->
  <g transform={sourceMarkerTransform}>
    {#if descriptors.source === 'one'}
      <!-- Single bar perpendicular to edge -->
      <line x1="-6" y1="0" x2="6" y2="0" stroke={markerColor} stroke-width="2" />
    {:else if descriptors.source === 'zero_or_one'}
      <!-- Bar toward node, circle toward edge -->
      <line x1="-6" y1="-4" x2="6" y2="-4" stroke={markerColor} stroke-width="2" />
      <circle cx="0" cy="6" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
    {:else if descriptors.source === 'zero_or_many'}
      <!-- Trident toward node (negative Y), circle toward edge (positive Y) -->
      <line x1="0" y1="-2" x2="-5" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="0" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="5" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <circle cx="0" cy="8" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
    {:else}
      <!-- many: just trident toward node -->
      <line x1="0" y1="-2" x2="-5" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="0" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="5" y2="-10" stroke={markerColor} stroke-width="1.5" />
    {/if}
  </g>

  <!-- Target marker: trident points TOWARD node (negative Y), circle AWAY (positive Y = toward edge) -->
  <g transform={targetMarkerTransform}>
    {#if descriptors.target === 'one'}
      <!-- Single bar perpendicular to edge -->
      <line x1="-6" y1="0" x2="6" y2="0" stroke={markerColor} stroke-width="2" />
    {:else if descriptors.target === 'zero_or_one'}
      <!-- Bar toward node, circle toward edge -->
      <line x1="-6" y1="-4" x2="6" y2="-4" stroke={markerColor} stroke-width="2" />
      <circle cx="0" cy="6" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
    {:else if descriptors.target === 'zero_or_many'}
      <!-- Trident toward node (negative Y), circle toward edge (positive Y) -->
      <line x1="0" y1="-2" x2="-5" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="0" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="5" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <circle cx="0" cy="8" r="4" fill="none" stroke={markerColor} stroke-width="1.5" />
    {:else}
      <!-- many: just trident toward node -->
      <line x1="0" y1="-2" x2="-5" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="0" y2="-10" stroke={markerColor} stroke-width="1.5" />
      <line x1="0" y1="-2" x2="5" y2="-10" stroke={markerColor} stroke-width="1.5" />
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
