<script lang="ts">
  import { 
    BaseEdge, 
    EdgeLabel,
    type EdgeProps,
    useSvelteFlow
  } from '@xyflow/svelte';
  import { edges, nodes, viewMode, dbtModels } from '$lib/stores';
  import Icon from '@iconify/svelte';
  import {
    getNodeDimensions,
    getNodeAbsolutePosition,
    getNodeCenter,
    calculateConnectionInfo,
    getSideRotation,
    calculateMarkerPosition,
    type Side
  } from '$lib/edge-utils';
  import {
    calculateBaseOffset,
    calculateLabelPositionWithContext,
    buildEdgePathWithContext,
    MARKER_PADDING,
    type EdgeCalculationContext
  } from '$lib/utils/edge-calculations';

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
  const baseOffset = $derived.by(() => calculateBaseOffset(parallelIndex, totalParallel));

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

  // Calculate optimal connection points using utility functions
  const connectionInfo = $derived.by(() => {
    return calculateConnectionInfo(sourceNode, targetNode, $nodes);
  });

  const isSelfEdge = $derived(source === target);

  // Build the edge path
  const edgePath = $derived.by(() => {
    const context: EdgeCalculationContext = {
      parallelIndex,
      totalParallel,
      sourceSide: connectionInfo.sourceSide,
      targetSide: connectionInfo.targetSide,
      sourcePoint: connectionInfo.sourcePoint,
      targetPoint: connectionInfo.targetPoint,
      isSelfEdge,
      storedOffsetX,
      storedOffsetY,
      dragOffsetX,
      dragOffsetY
    };
    return buildEdgePathWithContext(context);
  });


  // Label position at the middle of the edge
  const edgeLabelPos = $derived.by(() => {
    const context: EdgeCalculationContext = {
      parallelIndex,
      totalParallel,
      sourceSide: connectionInfo.sourceSide,
      targetSide: connectionInfo.targetSide,
      sourcePoint: connectionInfo.sourcePoint,
      targetPoint: connectionInfo.targetPoint,
      isSelfEdge,
      storedOffsetX,
      storedOffsetY,
      dragOffsetX,
      dragOffsetY
    };
    return calculateLabelPositionWithContext(context);
  });

  // Use raw data.label for input value, default to empty
  let label = $derived((data?.label as string) || '');
  let type = $derived((data?.type as string) || 'one_to_many');
  
  // Get models array from edge data
  const edgeModels = $derived((data?.models as any[]) || []);
  const modelCount = $derived((data?.modelCount as number) || edgeModels.length || 0);

  // Get active models for source and target nodes (prefer ephemeral active model data)
  const sourceNodeData = $derived(sourceNode?.data as any);
  const targetNodeData = $derived(targetNode?.data as any);
  
  const resolveActiveModel = (nodeData: any) => {
    // Prefer explicit active model id if present
    if (nodeData?._activeModelId) {
      const byId = $dbtModels.find((m) => m.unique_id === nodeData._activeModelId);
      if (byId) return byId;
    }
    // Next: ephemeral active model name/version
    if (nodeData?._activeModelName) {
      return {
        name: nodeData._activeModelName as string,
        version: nodeData._activeModelVersion as number | null | undefined,
      };
    }
    // Next: primary bound model
    if (nodeData?.dbt_model) {
      const byPrimary = $dbtModels.find((m) => m.unique_id === nodeData.dbt_model);
      if (byPrimary) return byPrimary;
    }
    // Next: first additional model
    const firstAdditional = (nodeData?.additional_models as string[] | undefined)?.[0] || null;
    if (firstAdditional) {
      const byAdditional = $dbtModels.find((m) => m.unique_id === firstAdditional);
      if (byAdditional) return byAdditional;
    }
    return null;
  };
  
  const sourceActiveModel = $derived(resolveActiveModel(sourceNodeData));
  const targetActiveModel = $derived(resolveActiveModel(targetNodeData));
  
  // Normalize model info for matching/display: if model names are missing, fall back to resolved active models
  const normalizedEdgeModels = $derived.by(() =>
    edgeModels.map((m: any) => ({
      source_model_name: m.source_model_name || sourceActiveModel?.name || null,
      source_model_version:
        m.source_model_version === undefined
          ? (sourceActiveModel ? sourceActiveModel.version ?? null : null)
          : m.source_model_version ?? null,
      target_model_name: m.target_model_name || targetActiveModel?.name || null,
      target_model_version:
        m.target_model_version === undefined
          ? (targetActiveModel ? targetActiveModel.version ?? null : null)
          : m.target_model_version ?? null,
      source_field: m.source_field,
      target_field: m.target_field,
    }))
  );
  
  const normalizeVersion = (v: number | null | undefined) =>
    v === undefined ? null : v;

  // Find matching model relationship based on active models
  const activeModelRelationship = $derived.by(() => {
    if (!sourceActiveModel || !targetActiveModel || normalizedEdgeModels.length === 0) {
      return null;
    }
    
    // Match by model name and version
    return normalizedEdgeModels.find((m: any) => {
      const srcVer = normalizeVersion(m.source_model_version as number | null | undefined);
      const tgtVer = normalizeVersion(m.target_model_version as number | null | undefined);
      const activeSrcVer = normalizeVersion(sourceActiveModel.version as number | null | undefined);
      const activeTgtVer = normalizeVersion(targetActiveModel.version as number | null | undefined);

      const sourceMatch = 
        m.source_model_name === sourceActiveModel.name &&
        (srcVer === null || srcVer === activeSrcVer);
      const targetMatch = 
        m.target_model_name === targetActiveModel.name &&
        (tgtVer === null || tgtVer === activeTgtVer);
      return sourceMatch && targetMatch;
    });
  });
  
  const firstModelRelationship = $derived(edgeModels[0] || null);
  const firstNormalizedRelationship = $derived(normalizedEdgeModels[0] || null);

  // Use active model relationship fields if available, otherwise fall back to first model or edge defaults
  let sourceField = $derived(
    activeModelRelationship?.source_field || 
    firstNormalizedRelationship?.source_field ||
    (data?.source_field as string) || 
    ''
  );
  let targetField = $derived(
    activeModelRelationship?.target_field || 
    firstNormalizedRelationship?.target_field ||
    (data?.target_field as string) || 
    ''
  );
  
  // Display text for collapsed state - show label or placeholder
  const displayLabel = $derived(label?.trim() || 'relates to');
  
  // Compact label calculations for overflow prevention
  const maxLabelWidth = $derived(Math.min(displayLabel.length * 7 + 16, 200));
  const truncatedLabel = $derived(displayLabel.length > 25 ? displayLabel.substring(0, 22) + '...' : displayLabel);
  
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
  const entityLabelSource = $derived((sourceNode?.data?.label as string) || 'Source');
  const entityLabelTarget = $derived((targetNode?.data?.label as string) || 'Target');

  // Prefer active model names for display; fall back to relationship model names, then entity labels
  const sourceName = $derived(
    sourceActiveModel?.name ||
    activeModelRelationship?.source_model_name ||
    entityLabelSource
  );
  const targetName = $derived(
    targetActiveModel?.name ||
    activeModelRelationship?.target_model_name ||
    entityLabelTarget
  );
  const actionText = $derived(label?.trim() || 'relates to');
  
  const relationText = $derived(
    `${descriptors.source} '${sourceName}' ${actionText} ${descriptors.target} '${targetName}'`
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

  /**
   * Swap relationship direction.
   * 
   * Swaps source ↔ target and source_field ↔ target_field to reverse the relationship direction.
   * Updates relationship type accordingly:
   * - one_to_many ↔ many_to_one (swaps cardinality)
   * - one_to_one → remains one_to_one (just swaps direction)
   * - many_to_many → remains many_to_many (just swaps direction)
   * 
   * Also updates all models array entries if multiple models exist, ensuring consistency
   * across all model relationships for this edge.
   */
  function swapDirection(e: MouseEvent) {
    // Explicitly stop propagation at all levels
    e.stopPropagation();
    e.stopImmediatePropagation();
    
    // Get current edge data
    const currentEdge = $edges.find(e => e.id === id);
    if (!currentEdge) return;
    
    // Don't swap source/target - keep the arrow direction the same
    const newSource = source;
    const newTarget = target;
    
    // Edge ID stays the same since we're not changing direction
    const newEdgeId = id;
    
    // Don't swap fields - they stay with their entities
    const newSourceField = sourceField;
    const newTargetField = targetField;
    
    // Only swap the relationship type
    // This moves the FK from one side to the other while keeping the visual direction
    // For example: "cool_stuff → department" with type "many_to_one" (FK on cool_stuff)
    // becomes: "cool_stuff → department" with type "one_to_many" (FK on department)
    let newType = type;
    if (type === 'one_to_many') {
      newType = 'many_to_one';
    } else if (type === 'many_to_one') {
      newType = 'one_to_many';
    }
    
    // Models array doesn't need to be swapped since we're not changing direction
    // We're only changing the type, which affects FK location but not the arrow direction
    const currentModels = (currentEdge.data?.models as any[]) || [];
    
    // Update edge with swapped values
    edges.update((list) =>
      list.map((edge) =>
        edge.id === id
          ? {
              ...edge,
              id: newEdgeId,
              source: newSource,
              target: newTarget,
              data: {
                ...(edge.data || {}),
                source_field: newSourceField,
                target_field: newTargetField,
                type: newType,
                models: currentModels.length > 0 ? currentModels : edge.data?.models,
              }
            }
          : edge
      )
    );
  }

  function selectThisEdge(e: Event) {
    e.stopPropagation();
    // Deselect all edges and select this one
    $edges = $edges.map(edge => ({
      ...edge,
      selected: edge.id === id
    }));
  }
  
  function handleCompactLabelKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      selectThisEdge(e);
    }
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
  const edgeStyle = $derived.by(() => {
    if (selected) {
      return `stroke: #26A69A; stroke-width: 2; ${style || ''}`;
    }

    // Ensure default stroke styling when not selected - using very light gray
    const defaultStyle = 'stroke: #cbd5e1; stroke-width: 2'; // Very light gray for edges
    return style ? `${defaultStyle}; ${style}` : defaultStyle;
  });

  // Crow's foot marker positions and rotations based on connection sides
  const markerColor = $derived(selected ? '#26A69A' : '#64748b');

  // Constants imported from edge-calculations

  const sourceMarkerTransform = $derived.by(() => {
    const { sourceSide, sourcePoint } = connectionInfo;
    const pos = calculateMarkerPosition(sourcePoint, sourceSide, baseOffset, MARKER_PADDING);
    return `translate(${pos.x} ${pos.y}) rotate(${getSideRotation(sourceSide)})`;
  });

  const targetMarkerTransform = $derived.by(() => {
    const { targetSide, targetPoint } = connectionInfo;
    const pos = calculateMarkerPosition(targetPoint, targetSide, baseOffset, MARKER_PADDING);
    return `translate(${pos.x} ${pos.y}) rotate(${getSideRotation(targetSide)})`;
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
        <button 
            class="text-slate-600 hover:text-[#26A69A] hover:bg-white rounded px-1.5 py-0.5 cursor-pointer bg-slate-100 border border-slate-300 flex items-center justify-center"
            onclick={swapDirection}
            title="Swap which table has the foreign key (moves FK to opposite side)"
            type="button"
            aria-label="Swap foreign key location"
        >
            <Icon icon="lucide:arrow-left-right" class="w-3 h-3" />
        </button>
      </div>
      <div class="text-[10px] text-slate-500 text-center truncate max-w-full" title={relationText}>
        {relationText}
      </div>
      <!-- Field mappings - show in Logical view -->
      {#if $viewMode === "logical"}
        {#if sourceField || targetField}
          <!-- Show field details (active model if matched, else fallback) -->
          <div class="text-[9px] text-slate-500 text-center border-t border-slate-200 pt-1 mt-0.5">
            <span class="font-mono"><span class="text-slate-400">{sourceName.toLowerCase()}.</span>{sourceField || '?'}</span>
            <span class="text-slate-400 mx-1">→</span>
            <span class="font-mono"><span class="text-slate-400">{targetName.toLowerCase()}.</span>{targetField || '?'}</span>
          </div>
        {:else if modelCount > 1}
          <!-- Show summary badge when multiple models exist but no fields resolved -->
          <div class="text-[9px] text-slate-400 text-center border-t border-slate-200 pt-1 mt-0.5">
            {modelCount} model{modelCount !== 1 ? 's' : ''}
          </div>
        {/if}
      {/if}
    </div>
  </EdgeLabel>
{:else}
  <!-- Compact text-only view - use EdgeLabel (HTML overlay) to render on top of all edge paths -->
  <EdgeLabel x={edgeLabelPos.x} y={edgeLabelPos.y} style="background: transparent; pointer-events: none;">
    <div
      class="pointer-events-auto nodrag nopan inline-block px-2 py-0.5 rounded bg-[#f8fafc] border border-[#e2e8f0] cursor-move select-none text-center"
      style="width: {maxLabelWidth}px;"
      onclick={(e) => {
        e.stopPropagation();
        selectThisEdge(e as unknown as MouseEvent);
      }}
      onpointerdown={(e) => {
        e.stopPropagation();
        startLabelDrag(e);
      }}
      onkeydown={handleCompactLabelKeydown}
      role="button"
      tabindex="0"
    >
      <span
        class="pointer-events-none text-[11px] font-medium text-[#64748b]"
        style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
      >
        {truncatedLabel}
      </span>
    </div>
  </EdgeLabel>
{/if}
