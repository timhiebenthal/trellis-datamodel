<script lang="ts">
  import { 
    BaseEdge, 
    type EdgeProps,
    useSvelteFlow,
    getBezierPath,
  } from '@xyflow/svelte';
  import { computeEdgeHighlightState } from '$lib/edge-highlight-utils';

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
    selected,
    data,
  }: EdgeProps = $props();

  const { getNodes } = useSvelteFlow();

  // Get selected node IDs from nodes array
  // Exclude placeholders and layer bands from selection tracking
  const selectedNodeIds = $derived.by(() => {
    const nodes = getNodes();
    const selected = new Set<string>();
    for (const node of nodes) {
      if (node.selected && !node.hidden) {
        // Exclude placeholder nodes ("...") and layer band background nodes
        const nodeId = String(node.id);
        if (!nodeId.startsWith('placeholder-') && node.type !== 'layerBand') {
          selected.add(nodeId);
        }
      }
    }
    return selected;
  });

  // Helper to get node by ID
  const getNode = (nodeId: string) => {
    const nodes = getNodes();
    return nodes.find(n => String(n.id) === nodeId);
  };
  
  // #region agent log
  const sourceNodeExists = $derived.by(() => {
    const nodes = getNodes();
    const found = nodes.find(n => String(n.id) === source);
    return { exists: !!found, nodeId: source, totalNodes: nodes.length };
  });
  const targetNodeExists = $derived.by(() => {
    const nodes = getNodes();
    const found = nodes.find(n => String(n.id) === target);
    return { exists: !!found, nodeId: target, totalNodes: nodes.length };
  });
  $effect(() => {
    const src = sourceNodeExists();
    const tgt = targetNodeExists();
    if (!src.exists || !tgt.exists) {
      fetch('http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'LineageEdge.svelte:effect',message:'Edge missing node anchor',data:{edgeId:id,sourceExists:src.exists,targetExists:tgt.exists,source:source,target:target,totalNodes:src.totalNodes},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
    }
  });
  // #endregion

  // Compute highlight state
  const highlightState = $derived.by(() => {
    return computeEdgeHighlightState(
      { id, source, target, selected },
      selectedNodeIds,
      getNode
    );
  });

  // Check flags
  const isGhosted = $derived((data as any)?._ghosted ?? false);
  const isOverlay = $derived((data as any)?._overlay ?? false);

  // Apply visual styling based on highlight state
  // Visual hierarchy: selected (teal-600, 3px) > connected (teal-300, 2.5px) > unselected (slate-500, 2px)
  // Ghosted edges have reduced opacity regardless of highlight state
  const edgeStyle = $derived.by(() => {
    const { highlightLevel } = highlightState;
    
    let strokeColor: string;
    let strokeWidth: number;
    let opacity: number;
    
    if (isOverlay) {
      strokeColor = '#22c55e'; // green-500
      strokeWidth = 1.5;
      opacity = 0.55;
    } else {
      switch (highlightLevel) {
        case 'selected':
          strokeColor = '#26A69A'; // teal-600
          strokeWidth = 3;
          opacity = 1.0;
          break;
        case 'connected':
          strokeColor = '#26A69A'; // teal-600
          strokeWidth = 2.5;
          opacity = 0.7;
          break;
        default:
          strokeColor = '#94a3b8'; // slate-400
          strokeWidth = 1.5;
          opacity = 0.8;
      }
    }
    
    if (isGhosted) {
      opacity = opacity * 0.3;
    }
    
    const baseStyle = `stroke: ${strokeColor}; stroke-width: ${strokeWidth}; opacity: ${opacity};`;
    return style ? `${baseStyle} ${style}` : baseStyle;
  });

  // Use Svelte Flow's built-in bezier path calculation
  const edgePath = $derived.by(() => {
    // getBezierPath returns [path, labelX, labelY, offsetX, offsetY]
    const [path] = getBezierPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
      sourcePosition,
      targetPosition,
    });
    return path;
  });
</script>

<BaseEdge path={edgePath} {markerEnd} style={edgeStyle} />

