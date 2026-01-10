/**
 * Edge calculation utilities for CustomEdge component
 * Extracted for testability and reusability
 */

import type { Point } from '$lib/edge-utils';
import type { Side } from '$lib/edge-utils';

/**
 * Context for edge calculations
 */
export interface EdgeCalculationContext {
  parallelIndex: number;
  totalParallel: number;
  isSelfEdge: boolean;
}

/**
 * Calculation constants
 */
export const EDGE_CALCULATION_CONSTANTS = {
  /** Spacing between parallel edges in pixels */
  PARALLEL_EDGE_SPACING: 50,
  
  /** Radius for self-loop curves */
  LOOP_RADIUS: 60,
  
  /** Padding to offset markers from node border */
  MARKER_PADDING: 8,
  
  /** Extra padding for label positioning on self-loops */
  LOOP_LABEL_OFFSET: 20
} as const;

/**
 * Calculate base offset for parallel edges - spreads them out horizontally/vertically
 * @param context Edge calculation context containing parallel edge info
 * @returns Offset value to apply perpendicular to edge direction
 */
export function calculateBaseOffset(context: EdgeCalculationContext): number {
  const { parallelIndex, totalParallel } = context;
  
  if (totalParallel <= 1) return 0;
  
  const spacing = EDGE_CALCULATION_CONSTANTS.PARALLEL_EDGE_SPACING;
  const totalWidth = (totalParallel - 1) * spacing;
  return (parallelIndex * spacing) - (totalWidth / 2);
}

/**
 * Calculate label position at the middle of the edge
 * @param connectionInfo Connection info with source/target points and sides
 * @param baseOffset Offset for parallel edges
 * @param isSelfEdge Whether this is a self-loop edge
 * @param storedOffsetX User-dragged X offset
 * @param storedOffsetY User-dragged Y offset
 * @param dragOffsetX Current drag offset X
 * @param dragOffsetY Current drag offset Y
 * @returns Label position {x, y}
 */
export function calculateLabelPosition(
  connectionInfo: {
    sourceSide: Side;
    targetSide: Side;
    sourcePoint: Point;
    targetPoint: Point;
  },
  baseOffset: number,
  isSelfEdge: boolean,
  storedOffsetX: number,
  storedOffsetY: number,
  dragOffsetX: number,
  dragOffsetY: number
): Point {
  const { sourceSide, targetSide, sourcePoint, targetPoint } = connectionInfo;

  // Special handling for self-loops: position label outside the loop curve
  if (isSelfEdge) {
    const midY = (sourcePoint.y + targetPoint.y) / 2 + baseOffset;
    const loopRadius = EDGE_CALCULATION_CONSTANTS.LOOP_RADIUS;
    const labelOffset = loopRadius + EDGE_CALCULATION_CONSTANTS.LOOP_LABEL_OFFSET;
    const midX = sourcePoint.x + labelOffset + storedOffsetX + dragOffsetX;
    return { x: midX, y: midY + storedOffsetY + dragOffsetY };
  }

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
}

/**
 * Build edge path string for SVG
 * @param sourcePoint Source connection point
 * @param targetPoint Target connection point
 * @param sourceSide Side of source node
 * @param targetSide Side of target node
 * @param baseOffset Offset for parallel edges
 * @param isSelfEdge Whether this is a self-loop edge
 * @param labelOffsetX User-dragged X offset for label positioning
 * @param labelOffsetY User-dragged Y offset for label positioning
 * @returns SVG path string
 */
export function buildEdgePath(
  sourcePoint: Point,
  targetPoint: Point,
  sourceSide: Side,
  targetSide: Side,
  baseOffset: number,
  isSelfEdge: boolean,
  labelOffsetX: number,
  labelOffsetY: number
): string {
  if (isSelfEdge) {
    return buildSelfLoopPath(sourcePoint, targetPoint, sourceSide, baseOffset);
  }
  return buildOrthogonalPath(
    sourcePoint,
    targetPoint,
    sourceSide,
    targetSide,
    baseOffset,
    labelOffsetX,
    labelOffsetY
  );
}

/**
 * Build a self-loop path that exits and re-enters the same node
 * @param sourcePoint Source connection point
 * @param targetPoint Target connection point
 * @param side Side of the node for the loop
 * @param baseOffset Offset for parallel edges
 * @returns SVG path string for self-loop
 */
function buildSelfLoopPath(
  sourcePoint: Point,
  targetPoint: Point,
  side: Side,
  baseOffset: number
): string {
  let sX = sourcePoint.x;
  let sY = sourcePoint.y;
  let tX = targetPoint.x;
  let tY = targetPoint.y;

  const loopRadius = EDGE_CALCULATION_CONSTANTS.LOOP_RADIUS;

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
 * Build orthogonal SVG path between two connection points
 * @param sourcePoint Source connection point
 * @param targetPoint Target connection point
 * @param sourceSide Side of source node
 * @param targetSide Side of target node
 * @param baseOffset Offset for parallel edges
 * @param labelOffsetX User-dragged X offset for label positioning
 * @param labelOffsetY User-dragged Y offset for label positioning
 * @returns SVG path string for orthogonal path
 */
function buildOrthogonalPath(
  sourcePoint: Point,
  targetPoint: Point,
  sourceSide: Side,
  targetSide: Side,
  baseOffset: number,
  labelOffsetX: number,
  labelOffsetY: number
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
