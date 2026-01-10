/**
 * Edge calculation utilities for CustomEdge component
 * Extracts complex calculations for better testability and maintainability
 */

import type { Side } from '$lib/edge-utils';

export interface Point {
  x: number;
  y: number;
}

export interface EdgeCalculationContext {
  parallelIndex: number;
  totalParallel: number;
  sourceSide: Side;
  targetSide: Side;
  sourcePoint: Point;
  targetPoint: Point;
  isSelfEdge: boolean;
  storedOffsetX: number;
  storedOffsetY: number;
  dragOffsetX: number;
  dragOffsetY: number;
}

// Constants extracted from CustomEdge component
export const EDGE_CALCULATION_CONSTANTS = {
  PARALLEL_EDGE_SPACING: 50, // pixels between parallel edges
  LOOP_RADIUS: 60, // stable loop radius for self-loops
  MARKER_PADDING: 8, // padding to offset markers from node border
  LOOP_LABEL_OFFSET: 20 // extra padding for label readability on self-loops
} as const;

// Re-export MARKER_PADDING for convenience
export const MARKER_PADDING = EDGE_CALCULATION_CONSTANTS.MARKER_PADDING;

/**
 * Calculate base offset for parallel edges
 * Spreads parallel edges out horizontally to prevent overlap
 * Accepts either (context) or (parallelIndex, totalParallel)
 */
export function calculateBaseOffset(
  param1: EdgeCalculationContext | number,
  param2?: number
): number {
  let parallelIndex: number;
  let totalParallel: number;

  if (typeof param1 === 'object' && 'parallelIndex' in param1) {
    // Signature: calculateBaseOffset(context)
    parallelIndex = param1.parallelIndex;
    totalParallel = param1.totalParallel;
  } else {
    // Signature: calculateBaseOffset(parallelIndex, totalParallel)
    parallelIndex = param1 as number;
    totalParallel = param2 ?? 1;
  }

  if (totalParallel <= 1) return 0;
  const totalWidth = (totalParallel - 1) * EDGE_CALCULATION_CONSTANTS.PARALLEL_EDGE_SPACING;
  return (parallelIndex * EDGE_CALCULATION_CONSTANTS.PARALLEL_EDGE_SPACING) - (totalWidth / 2);
}

/**
 * Calculate label position based on edge configuration
 * Handles both regular edges and self-loops
 */
export function calculateLabelPosition(
  connectionInfo: { sourceSide: Side; targetSide: Side; sourcePoint: Point; targetPoint: Point },
  baseOffset: number,
  isSelfEdge: boolean,
  storedOffsetX: number,
  storedOffsetY: number,
  dragOffsetX: number,
  dragOffsetY: number
): Point {
  const { sourceSide, sourcePoint, targetPoint } = connectionInfo;

  // Special handling for self-loops: position label outside the loop curve
  if (isSelfEdge) {
    const midY = (sourcePoint.y + targetPoint.y) / 2 + baseOffset;
    // Position label to the right of the node edge, offset by loop radius + padding
    const midX = sourcePoint.x + EDGE_CALCULATION_CONSTANTS.LOOP_RADIUS + EDGE_CALCULATION_CONSTANTS.LOOP_LABEL_OFFSET + storedOffsetX + dragOffsetX;
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
 * Calculate label position using EdgeCalculationContext
 * Convenience wrapper for easier component integration
 */
export function calculateLabelPositionWithContext(context: EdgeCalculationContext): Point {
  return calculateLabelPosition(
    {
      sourceSide: context.sourceSide,
      targetSide: context.targetSide,
      sourcePoint: context.sourcePoint,
      targetPoint: context.targetPoint
    },
    calculateBaseOffset(context.parallelIndex, context.totalParallel),
    context.isSelfEdge,
    context.storedOffsetX,
    context.storedOffsetY,
    context.dragOffsetX,
    context.dragOffsetY
  );
}

/**
 * Build edge path string for SVG
 * Handles both orthogonal paths and self-loops
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
  let sX = sourcePoint.x;
  let sY = sourcePoint.y;
  let tX = targetPoint.x;
  let tY = targetPoint.y;

  if (isSelfEdge) {
    // Apply parallel edge offset perpendicular to exit direction
    if (sourceSide === 'left' || sourceSide === 'right') {
      sY += baseOffset;
      tY += baseOffset;
    } else {
      sX += baseOffset;
      tX += baseOffset;
    }

    const horizontalOffset =
      sourceSide === 'left' || sourceSide === 'right'
        ? EDGE_CALCULATION_CONSTANTS.LOOP_RADIUS * (sourceSide === 'left' ? -1 : 1)
        : 0;

    // Use a cubic curve to create a smooth loop on side of node
    return `M ${sX} ${sY} C ${sX + horizontalOffset} ${sY}, ${tX + horizontalOffset} ${tY}, ${tX} ${tY}`;
  }

  // Build orthogonal path for regular edges
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
 * Build edge path using EdgeCalculationContext
 * Convenience wrapper for easier component integration
 */
export function buildEdgePathWithContext(context: EdgeCalculationContext): string {
  return buildEdgePath(
    context.sourcePoint,
    context.targetPoint,
    context.sourceSide,
    context.targetSide,
    calculateBaseOffset(context.parallelIndex, context.totalParallel),
    context.isSelfEdge,
    context.storedOffsetX + context.dragOffsetX,
    context.storedOffsetY + context.dragOffsetY
  );
}
