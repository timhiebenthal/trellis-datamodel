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

  // Compute highlight state
  const highlightState = $derived.by(() => {
    return computeEdgeHighlightState(
      { id, source, target, selected },
      selectedNodeIds,
      getNode
    );
  });

  // Apply visual styling based on highlight state
  // Visual hierarchy: selected (teal-600, 3px) > connected (teal-300, 2.5px) > unselected (slate-500, 2px)
  const edgeStyle = $derived.by(() => {
    const { highlightLevel } = highlightState;
    
    let strokeColor: string;
    let strokeWidth: number;
    let opacity: number;
    
    switch (highlightLevel) {
      case 'selected':
        // Directly selected edge: most prominent
        strokeColor = '#26A69A'; // teal-600
        strokeWidth = 3;
        opacity = 1.0;
        break;
      case 'connected':
        // Edge connected to selected node: highlighted but less prominent
        strokeColor = '#26A69A'; // teal-600 (primary teal)
        strokeWidth = 2.5;
        opacity = 0.7;
        break;
      default:
        // Unselected edge: default styling - subtle grey, thin
        strokeColor = '#94a3b8'; // slate-400 (lighter grey)
        strokeWidth = 1.5;
        opacity = 0.8;
    }
    
    const baseStyle = `stroke: ${strokeColor}; stroke-width: ${strokeWidth}; opacity: ${opacity}`;
    return style ? `${baseStyle}; ${style}` : baseStyle;
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

