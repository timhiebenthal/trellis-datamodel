import type { Node } from "@xyflow/svelte";

/**
 * Entity type classification for dimensional modeling
 */
export type EntityType = "fact" | "dimension" | "unclassified";

/**
 * Position coordinates in 2D space
 */
export interface Position {
    x: number;
    y: number;
}

/**
 * Configuration for smart positioning algorithms
 */
export interface PositioningConfig {
    /**
     * Default center X coordinate when no entities exist
     */
    defaultCenterX?: number;

    /**
     * Default center Y coordinate when no entities exist
     */
    defaultCenterY?: number;

    /**
     * Minimum radius for dimension entity placement from center
     */
    dimensionMinRadius?: number;

    /**
     * Maximum additional radius offset for dimension entities
     */
    dimensionRadiusOffset?: number;

    /**
     * Random offset range for fact entities (half-width from center)
     */
    factOffsetRange?: number;
}

/**
 * Default positioning configuration
 */
const DEFAULT_CONFIG: Required<PositioningConfig> = {
    defaultCenterX: 500,
    defaultCenterY: 400,
    dimensionMinRadius: 500,
    dimensionRadiusOffset: 300,
    factOffsetRange: 200,
};

/**
 * Calculates the center point of the canvas based on existing entity positions.
 * If no entities exist, returns default center coordinates.
 *
 * @param nodes - Array of all nodes in the canvas
 * @param config - Optional positioning configuration
 * @returns Center coordinates as {x, y}
 *
 * @example
 * ```typescript
 * const center = calculateCanvasCenter(nodes);
 * // Returns { x: 500, y: 400 } for default center
 * ```
 */
export function calculateCanvasCenter(
    nodes: Node[],
    config?: PositioningConfig,
): Position {
    const { defaultCenterX, defaultCenterY } = { ...DEFAULT_CONFIG, ...config };

    // Filter for entity nodes only (not groups or other node types)
    const entityNodes = nodes.filter((n) => n.type === "entity");

    // If no entities exist, return default center
    if (entityNodes.length === 0) {
        return { x: defaultCenterX, y: defaultCenterY };
    }

    // Calculate center as midpoint of min/max positions
    const xPositions = entityNodes.map((n) => n.position.x);
    const yPositions = entityNodes.map((n) => n.position.y);

    const centerX = (Math.min(...xPositions) + Math.max(...xPositions)) / 2;
    const centerY = (Math.min(...yPositions) + Math.max(...yPositions)) / 2;

    return { x: centerX, y: centerY };
}

/**
 * Calculates position for a fact entity in dimensional modeling.
 * Fact entities are placed in the center area with a random offset.
 *
 * @param center - Center coordinates from calculateCanvasCenter
 * @param config - Optional positioning configuration
 * @returns Position coordinates for the fact entity
 *
 * @example
 * ```typescript
 * const center = { x: 500, y: 400 };
 * const position = calculateFactPosition(center);
 * // Returns random position like { x: 450, y: 380 }
 * ```
 */
export function calculateFactPosition(
    center: Position,
    config?: PositioningConfig,
): Position {
    const { factOffsetRange } = { ...DEFAULT_CONFIG, ...config };

    // Random offset within specified range (-range to +range)
    const offsetX = (Math.random() - 0.5) * 2 * factOffsetRange;
    const offsetY = (Math.random() - 0.5) * 2 * factOffsetRange;

    return {
        x: center.x + offsetX,
        y: center.y + offsetY,
    };
}

/**
 * Calculates position for a dimension entity in dimensional modeling.
 * Dimension entities are placed in an outer ring around the center.
 *
 * @param center - Center coordinates from calculateCanvasCenter
 * @param config - Optional positioning configuration
 * @returns Position coordinates for the dimension entity
 *
 * @example
 * ```typescript
 * const center = { x: 500, y: 400 };
 * const position = calculateDimensionPosition(center);
 * // Returns position on outer ring like { x: 950, y: 400 }
 * ```
 */
export function calculateDimensionPosition(
    center: Position,
    config?: PositioningConfig,
): Position {
    const { dimensionMinRadius, dimensionRadiusOffset } = {
        ...DEFAULT_CONFIG,
        ...config,
    };

    // Random radius within specified range
    const radius =
        dimensionMinRadius + Math.random() * dimensionRadiusOffset;

    // Random angle around full circle (0 to 2π)
    const angle = Math.random() * 2 * Math.PI;

    return {
        x: center.x + Math.cos(angle) * radius,
        y: center.y + Math.sin(angle) * radius,
    };
}

/**
 * Calculates position for an unclassified entity.
 * Uses simple random positioning in the top-left area.
 *
 * @returns Position coordinates for the unclassified entity
 *
 * @example
 * ```typescript
 * const position = calculateUnclassifiedPosition();
 * // Returns position like { x: 150, y: 180 }
 * ```
 */
export function calculateUnclassifiedPosition(): Position {
    return {
        x: 100 + Math.random() * 200,
        y: 100 + Math.random() * 200,
    };
}

/**
 * Smart positioning algorithm for dimensional modeling.
 * Automatically selects the appropriate positioning strategy based on entity type.
 *
 * - **fact**: Entities placed in center area with random offset
 * - **dimension**: Entities placed in outer ring around center
 * - **unclassified**: Simple random positioning
 *
 * @param entityType - Type of entity to position
 * @param nodes - Array of all nodes in the canvas (for center calculation)
 * @param config - Optional positioning configuration
 * @returns Calculated position for the new entity
 *
 * @example
 * ```typescript
 * const position = calculateSmartPosition("fact", nodes);
 * const dimPosition = calculateSmartPosition("dimension", nodes);
 * const unclassifiedPosition = calculateSmartPosition("unclassified", nodes);
 * ```
 */
export function calculateSmartPosition(
    entityType: EntityType,
    nodes: Node[],
    config?: PositioningConfig,
): Position {
    switch (entityType) {
        case "fact":
            const center = calculateCanvasCenter(nodes, config);
            return calculateFactPosition(center, config);

        case "dimension":
            const dimCenter = calculateCanvasCenter(nodes, config);
            return calculateDimensionPosition(dimCenter, config);

        case "unclassified":
            return calculateUnclassifiedPosition();

        default:
            // Fallback to unclassified for unknown types
            return calculateUnclassifiedPosition();
    }
}

/**
 * Determines if a position is within a specified distance of any existing entity.
 * Useful for preventing overlap when positioning new entities.
 *
 * @param position - Position to check
 * @param nodes - Array of existing nodes
 * @param minDistance - Minimum distance from other entities (default: 50)
 * @returns True if position is too close to another entity
 *
 * @example
 * ```typescript
 * const isTooClose = isPositionNearEntity({ x: 500, y: 400 }, nodes, 100);
 * if (isTooClose) {
 *   // Try a different position
 * }
 * ```
 */
export function isPositionNearEntity(
    position: Position,
    nodes: Node[],
    minDistance: number = 50,
): boolean {
    const entityNodes = nodes.filter((n) => n.type === "entity");

    for (const node of entityNodes) {
        const dx = position.x - node.position.x;
        const dy = position.y - node.position.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance <= minDistance) {
            return true;
        }
    }

    return false;
}

/**
 * Generates multiple candidate positions and returns one that's not near existing entities.
 * Useful for ensuring no overlap when placing new entities.
 *
 * @param entityType - Type of entity to position
 * @param nodes - Array of existing nodes
 * @param maxAttempts - Maximum positioning attempts (default: 10)
 * @param config - Optional positioning configuration
 * @returns A position that's not too close to existing entities
 *
 * @example
 * ```typescript
 * const position = findNonOverlappingPosition("fact", nodes);
 * ```
 */
export function findNonOverlappingPosition(
    entityType: EntityType,
    nodes: Node[],
    maxAttempts: number = 10,
    config?: PositioningConfig,
): Position {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const position = calculateSmartPosition(entityType, nodes, config);

        if (!isPositionNearEntity(position, nodes)) {
            return position;
        }
    }

    // If all attempts failed, return the last calculated position
    return calculateSmartPosition(entityType, nodes, config);
}
