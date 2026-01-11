import type { Node } from "@xyflow/svelte";
import type { Position } from "$lib/utils/position-utils";

/**
 * Configuration for dimensional model positioning
 */
export interface DimensionalModelConfig {
    /**
     * Default center X coordinate when no entities exist
     */
    defaultCenterX?: number;

    /**
     * Default center Y coordinate when no entities exist
     */
    defaultCenterY?: number;

    /**
     * Padding to add around groups when auto-sizing
     */
    groupPadding?: number;

    /**
     * Minimum width for groups
     */
    minGroupWidth?: number;

    /**
     * Minimum height for groups
     */
    minGroupHeight?: number;

    /**
     * Threshold for considering a size change significant (pixels)
     */
    sizeChangeThreshold?: number;

    /**
     * Additional height for logical view when entity is bound
     */
    logicalViewAdditionalHeight?: number;

    /**
     * Header + padding height for entity panels
     */
    entityHeaderHeight?: number;

    /**
     * Default entity height when estimated
     */
    defaultEntityHeight?: number;
}

/**
 * Result of group size calculation
 */
export interface GroupSizeResult {
    /** Group node ID */
    groupId: string;

    /** Calculated width */
    width: number;

    /** Calculated height */
    height: number;
}

/**
 * Result of all group sizes calculation
 */
export interface GroupSizesResult {
    /** Map of group IDs to their calculated sizes */
    sizes: Map<string, GroupSizeResult>;

    /** Whether any groups need updates */
    needsUpdate: boolean;
}

/**
 * Dimensional model positioner class.
 * Provides smart positioning algorithms for dimensional modeling data structures.
 *
 * Positions fact entities in center and dimension entities in an outer ring
 * to create a star schema visual representation.
 */
export class DimensionalModelPositioner {
    private config: Required<DimensionalModelConfig>;

    constructor(config?: DimensionalModelConfig) {
        this.config = {
            defaultCenterX: 500,
            defaultCenterY: 400,
            groupPadding: 40,
            minGroupWidth: 300,
            minGroupHeight: 200,
            sizeChangeThreshold: 5,
            logicalViewAdditionalHeight: 100,
            entityHeaderHeight: 80,
            defaultEntityHeight: 300,
            ...config,
        };
    }

    /**
     * Calculates center point of canvas based on existing entity positions.
     * If no entities exist, returns default center coordinates.
     *
     * @param nodes - Array of all nodes in the canvas
     * @returns Center coordinates as {x, y}
     */
    calculateCenter(nodes: Node[]): Position {
        // Filter for entity nodes only (not groups or other node types)
        const entityNodes = nodes.filter((n) => n.type === "entity");

        // If no entities exist, return default center
        if (entityNodes.length === 0) {
            return {
                x: this.config.defaultCenterX,
                y: this.config.defaultCenterY,
            };
        }

        // Calculate center as midpoint of min/max positions
        const xPositions = entityNodes.map((n) => n.position.x);
        const yPositions = entityNodes.map((n) => n.position.y);

        const centerX =
            (Math.min(...xPositions) + Math.max(...xPositions)) / 2;
        const centerY =
            (Math.min(...yPositions) + Math.max(...yPositions)) / 2;

        return { x: centerX, y: centerY };
    }

    /**
     * Calculates position for a fact entity in dimensional modeling.
     * Fact entities are placed in center area with a random offset.
     *
     * @param center - Center coordinates from calculateCenter
     * @returns Position coordinates for fact entity
     */
    calculateFactPosition(center: Position): Position {
        const factOffsetRange = 200;

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
     * @param center - Center coordinates from calculateCenter
     * @returns Position coordinates for dimension entity
     */
    calculateDimensionPosition(center: Position): Position {
        const dimensionMinRadius = 500;
        const dimensionRadiusOffset = 300;

        // Random radius within specified range
        const radius =
            dimensionMinRadius +
            Math.random() * dimensionRadiusOffset;

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
     * @returns Position coordinates for unclassified entity
     */
    calculateUnclassifiedPosition(): Position {
        return {
            x: 100 + Math.random() * 200,
            y: 100 + Math.random() * 200,
        };
    }

    /**
     * Smart positioning algorithm for dimensional modeling.
     * Automatically selects the appropriate positioning strategy based on entity type.
     *
     * @param entityType - Type of entity to position
     * @param nodes - Array of all nodes in the canvas (for center calculation)
     * @returns Calculated position for the new entity
     */
    calculateSmartPosition(
        entityType: "fact" | "dimension" | "unclassified",
        nodes: Node[],
    ): Position {
        const center = this.calculateCenter(nodes);

        switch (entityType) {
            case "fact":
                return this.calculateFactPosition(center);
            case "dimension":
                return this.calculateDimensionPosition(center);
            case "unclassified":
                return this.calculateUnclassifiedPosition();
            default:
                // Fallback to unclassified for unknown types
                return this.calculateUnclassifiedPosition();
        }
    }
}

/**
 * Group size calculator class.
 * Handles automatic sizing of group nodes to fit their children.
 */
export class GroupSizeCalculator {
    private config: Required<DimensionalModelConfig>;

    constructor(config?: DimensionalModelConfig) {
        this.config = {
            defaultCenterX: 500,
            defaultCenterY: 400,
            groupPadding: 40,
            minGroupWidth: 300,
            minGroupHeight: 200,
            sizeChangeThreshold: 5,
            logicalViewAdditionalHeight: 100,
            entityHeaderHeight: 80,
            defaultEntityHeight: 300,
            ...config,
        };
    }

    /**
     * Calculates effective height for a child node.
     * Handles measured dimensions, data dimensions, and view mode adjustments.
     *
     * @param child - Child node to calculate height for
     * @param viewMode - Current view mode ("conceptual" or "logical")
     * @returns Calculated height
     */
    private calculateChildHeight(
        child: Node,
        viewMode: "conceptual" | "logical",
    ): number {
        const measuredHeight = child.measured?.height;

        // If measured height is substantial (>= 50), use it directly
        if (measuredHeight !== undefined && measuredHeight >= 50) {
            return measuredHeight;
        }

        // If height is missing or small and not collapsed, estimate
        if (child.data?.collapsed === false) {
            const panelHeight = child.data?.panelHeight as number | undefined;
            const dataHeight = child.data?.height as number | undefined;

            // Use panelHeight if available, otherwise use data height
            let estimatedHeight: number;
            if (panelHeight && panelHeight > 0) {
                estimatedHeight = panelHeight;
            } else if (dataHeight !== undefined) {
                estimatedHeight = dataHeight;
            } else {
                estimatedHeight = this.config.defaultEntityHeight;
            }

            // Add header height only if we have panelHeight data
            if (panelHeight && panelHeight > 0) {
                estimatedHeight += this.config.entityHeaderHeight;
            }

            // Add extra height for logical view metadata if bound
            if (viewMode === "logical" && child.data?.dbt_model) {
                estimatedHeight += this.config.logicalViewAdditionalHeight;
            }

            return estimatedHeight;
        }

        // Fallback for collapsed or no data
        const fallbackHeight = measuredHeight ?? 0;
        return fallbackHeight > 0 ? fallbackHeight : 200;
    }

    /**
     * Calculates effective width for a child node.
     * Uses measured dimensions or falls back to data dimensions/defaults.
     *
     * @param child - Child node to calculate width for
     * @returns Calculated width
     */
    private calculateChildWidth(child: Node): number {
        const measuredWidth = child.measured?.width;

        const width =
            measuredWidth && measuredWidth > 0
                ? measuredWidth
                : ((child.data?.width as number) ?? 320);

        return width;
    }

    /**
     * Calculates required size for a single group.
     *
     * @param group - The group node
     * @param allNodes - All nodes in the canvas (to find children)
     * @param viewMode - Current view mode
     * @returns Calculated size or null if group should be skipped
     */
    private calculateGroupSize(
        group: Node,
        allNodes: Node[],
        viewMode: "conceptual" | "logical",
    ): GroupSizeResult | null {
        // Skip groups that have been manually resized
        if (group.data?.manuallyResized) {
            return null;
        }

        const children = allNodes.filter(
            (n) => n.parentId === group.id && !n.hidden,
        );

        if (children.length === 0) {
            return null;
        }

        let maxX = 0;
        let maxY = 0;

        for (const child of children) {
            const width = this.calculateChildWidth(child);
            const height = this.calculateChildHeight(child, viewMode);

            const right = child.position.x + width;
            const bottom = child.position.y + height;

            if (right > maxX) maxX = right;
            if (bottom > maxY) maxY = bottom;
        }

        // Add padding
        const newWidth = Math.max(
            maxX + this.config.groupPadding,
            this.config.minGroupWidth,
        );
        const newHeight = Math.max(
            maxY + this.config.groupPadding,
            this.config.minGroupHeight,
        );

        const currentWidth = (group.data.width as number) ?? 0;
        const currentHeight = (group.data.height as number) ?? 0;

        // Only update if difference is significant
        if (
            Math.abs(newWidth - currentWidth) >
                this.config.sizeChangeThreshold ||
            Math.abs(newHeight - currentHeight) >
                this.config.sizeChangeThreshold
        ) {
            return {
                groupId: group.id,
                width: newWidth,
                height: newHeight,
            };
        }

        return null;
    }

    /**
     * Calculates sizes for all groups in the canvas.
     *
     * @param nodes - All nodes in the canvas
     * @param viewMode - Current view mode ("conceptual" or "logical")
     * @param isDragging - Whether any node is currently being dragged
     * @returns Result with calculated sizes and update flag
     */
    calculateGroupSizes(
        nodes: Node[],
        viewMode: "conceptual" | "logical",
        isDragging: boolean,
    ): GroupSizesResult {
        // Skip updates during drag to prevent interruption
        if (isDragging || nodes.some((n) => n.dragging)) {
            return {
                sizes: new Map(),
                needsUpdate: false,
            };
        }

        const groups = nodes.filter(
            (n) => n.type === "group" && !n.data.collapsed,
        );

        if (groups.length === 0) {
            return {
                sizes: new Map(),
                needsUpdate: false,
            };
        }

        const sizes = new Map<string, GroupSizeResult>();

        for (const group of groups) {
            const result = this.calculateGroupSize(group, nodes, viewMode);
            if (result) {
                sizes.set(result.groupId, result);
            }
        }

        return {
            sizes,
            needsUpdate: sizes.size > 0,
        };
    }

    /**
     * Applies calculated group sizes to the nodes array.
     * Returns a new nodes array with updated group sizes.
     *
     * @param nodes - Current nodes array
     * @param sizes - Map of group IDs to their calculated sizes
     * @returns New nodes array with updated group sizes
     */
    applyGroupSizes(
        nodes: Node[],
        sizes: Map<string, GroupSizeResult>,
    ): Node[] {
        if (sizes.size === 0) {
            return nodes;
        }

        return nodes.map((n) => {
            if (sizes.has(n.id)) {
                const sizeResult = sizes.get(n.id)!;
                return {
                    ...n,
                    data: {
                        ...n.data,
                        width: sizeResult.width,
                        height: sizeResult.height,
                    },
                };
            }
            return n;
        });
    }
}
