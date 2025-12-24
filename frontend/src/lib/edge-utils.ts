/**
 * Edge routing utilities for CustomEdge component
 * Extracted for testability
 */

export type Side = 'top' | 'bottom' | 'left' | 'right';

export interface NodeDimensions {
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface ConnectionInfo {
  sourceSide: Side;
  targetSide: Side;
  sourcePoint: Point;
  targetPoint: Point;
}

/**
 * Build a self-loop path that exits and re-enters the same node
 */
export function buildSelfLoopPath(
  sourcePoint: Point,
  targetPoint: Point,
  side: Side = 'right',
  baseOffset: number = 0,
  loopRadius: number = 60
): string {
  let sX = sourcePoint.x;
  let sY = sourcePoint.y;
  let tX = targetPoint.x;
  let tY = targetPoint.y;

  // Apply parallel edge offset perpendicular to exit direction
  if (side === 'left' || side === 'right') {
    sY += baseOffset;
    tY += baseOffset;
  } else {
    sX += baseOffset;
    tX += baseOffset;
  }

  const horizontalOffset =
    side === 'left' || side === 'right'
      ? loopRadius * (side === 'left' ? -1 : 1)
      : 0;

  // Use a cubic curve to create a smooth loop on the side of the node
  return `M ${sX} ${sY} C ${sX + horizontalOffset} ${sY}, ${tX + horizontalOffset} ${tY}, ${tX} ${tY}`;
}

/**
 * Get node dimensions from node data
 * Prefers SvelteFlow's measured dimensions if available
 */
export function getNodeDimensions(node: any): NodeDimensions {
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

/**
 * Get absolute node position accounting for parent groups
 */
export function getNodeAbsolutePosition(node: any, nodes: any[]): Point {
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
    const parent = nodes.find(n => n.id === node.parentId);
    if (parent) {
      const parentPos = getNodeAbsolutePosition(parent, nodes);
      x += parentPos.x;
      y += parentPos.y;
    }
  }
  return { x, y };
}

/**
 * Get node center point
 */
export function getNodeCenter(node: any, nodes: any[]): Point {
  const pos = getNodeAbsolutePosition(node, nodes);
  const dim = getNodeDimensions(node);
  return {
    x: pos.x + dim.width / 2,
    y: pos.y + dim.height / 2
  };
}

/**
 * Calculate optimal connection sides and points based on node positions
 * Chooses the closest pair of sides to minimize edge length
 */
export function calculateConnectionInfo(
  sourceNode: any,
  targetNode: any,
  nodes: any[]
): ConnectionInfo {
  // Self-relationships: exit and re-enter on the right side with a loop
  const isSameNode =
    (sourceNode && targetNode && sourceNode === targetNode) ||
    (sourceNode?.id && targetNode?.id && sourceNode.id === targetNode.id);

  if (isSameNode) {
    const center = getNodeCenter(sourceNode, nodes);
    const dim = getNodeDimensions(sourceNode);
    const halfHeight = dim.height / 2;

    // Keep markers away from corners while staying within the node's height
    const verticalOffset = Math.min(
      Math.max(dim.height * 0.25, 16),
      Math.max(halfHeight - 12, 16)
    );

    const edgeX = center.x + dim.width / 2;
    return {
      sourceSide: 'right',
      targetSide: 'right',
      sourcePoint: { x: edgeX, y: center.y - verticalOffset },
      targetPoint: { x: edgeX, y: center.y + verticalOffset }
    };
  }

  const sourceCenter = getNodeCenter(sourceNode, nodes);
  const targetCenter = getNodeCenter(targetNode, nodes);
  const sourceDim = getNodeDimensions(sourceNode);
  const targetDim = getNodeDimensions(targetNode);
  
  const dx = targetCenter.x - sourceCenter.x;
  const dy = targetCenter.y - sourceCenter.y;
  
  let sourceSide: Side;
  let targetSide: Side;
  let sourcePoint: Point;
  let targetPoint: Point;
  
  // Choose sides based on relative positions - pick closest pair
  if (Math.abs(dx) > Math.abs(dy)) {
    // Horizontal arrangement - use left/right sides
    if (dx > 0) {
      sourceSide = 'right';
      targetSide = 'left';
      sourcePoint = { x: sourceCenter.x, y: sourceCenter.y };
      targetPoint = { x: targetCenter.x, y: targetCenter.y };
    } else {
      sourceSide = 'left';
      targetSide = 'right';
      sourcePoint = { x: sourceCenter.x, y: sourceCenter.y };
      targetPoint = { x: targetCenter.x, y: targetCenter.y };
    }
  } else {
    // Vertical arrangement - use top/bottom sides
    if (dy > 0) {
      sourceSide = 'bottom';
      targetSide = 'top';
      sourcePoint = { x: sourceCenter.x, y: sourceCenter.y };
      targetPoint = { x: targetCenter.x, y: targetCenter.y };
    } else {
      sourceSide = 'top';
      targetSide = 'bottom';
      sourcePoint = { x: sourceCenter.x, y: sourceCenter.y };
      targetPoint = { x: targetCenter.x, y: targetCenter.y };
    }
  }
  
  return { sourceSide, targetSide, sourcePoint, targetPoint };
}

/**
 * Get rotation angle for crow's foot marker based on connection side
 * Markers are drawn with trident at negative Y (pointing UP at 0°)
 * The side indicates which side of the NODE the connection is on
 * Markers always point TOWARD the node they belong to
 */
export function getSideRotation(side: Side): number {
  switch (side) {
    case 'bottom': return 0;    // Marker points UP (toward node above)
    case 'top': return 180;     // Marker points DOWN (toward node below)
    case 'left': return 90;     // Marker points RIGHT (toward node on right)
    case 'right': return -90;   // Marker points LEFT (toward node on left)
  }
}

/**
 * Build orthogonal SVG path between two connection points
 */
export function buildOrthogonalPath(
  sourcePoint: Point,
  targetPoint: Point,
  sourceSide: Side,
  targetSide: Side,
  baseOffset: number = 0,
  labelOffsetX: number = 0,
  labelOffsetY: number = 0
): string {
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
    const midX = (sX + tX) / 2 + labelOffsetX;
    return `M ${sX} ${sY} L ${midX} ${sY} L ${midX} ${tY} L ${tX} ${tY}`;
  } else if (sourceSide === 'left' && targetSide === 'right') {
    // Horizontal: left → right
    const midX = (sX + tX) / 2 + labelOffsetX;
    return `M ${sX} ${sY} L ${midX} ${sY} L ${midX} ${tY} L ${tX} ${tY}`;
  } else if (sourceSide === 'bottom' && targetSide === 'top') {
    // Vertical: down → up
    const midY = (sY + tY) / 2 + labelOffsetY;
    return `M ${sX} ${sY} L ${sX} ${midY} L ${tX} ${midY} L ${tX} ${tY}`;
  } else {
    // Vertical: up → down (top → bottom)
    const midY = (sY + tY) / 2 + labelOffsetY;
    return `M ${sX} ${sY} L ${sX} ${midY} L ${tX} ${midY} L ${tX} ${tY}`;
  }
}

/**
 * Calculate marker position with padding offset from node border
 */
export function calculateMarkerPosition(
  point: Point,
  side: Side,
  baseOffset: number,
  padding: number
): Point {
  let x = point.x;
  let y = point.y;
  
  // Apply parallel edge offset
  if (side === 'left' || side === 'right') {
    y += baseOffset;
  } else {
    x += baseOffset;
  }
  
  // Apply padding away from node border
  switch (side) {
    case 'top': y -= padding; break;
    case 'bottom': y += padding; break;
    case 'left': x -= padding; break;
    case 'right': x += padding; break;
  }
  
  return { x, y };
}

