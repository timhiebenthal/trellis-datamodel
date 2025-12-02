import type { Node, Edge } from "@xyflow/svelte";
import ELK from "elkjs/lib/elk.bundled.js";

export interface LayoutOptions {
    direction?: "TB" | "LR";
    nodeSpacing?: number;
    rankSpacing?: number;
}

const DEFAULT_OPTIONS: Required<LayoutOptions> = {
    direction: "LR",
    nodeSpacing: 100,
    rankSpacing: 150,
};

// Single ELK instance (lazy-loaded on client)
let elkInstance: InstanceType<typeof ELK> | null = null;

function getElk(): InstanceType<typeof ELK> | null {
    if (typeof window === "undefined") {
        return null; // SSR
    }
    if (!elkInstance) {
        elkInstance = new ELK();
    }
    return elkInstance;
}

function getNodeDimensions(node: Node): { width: number; height: number } {
    const width = (node.data?.width as number) || 280;
    const panelHeight = (node.data?.panelHeight as number) || 200;
    const collapsed = node.data?.collapsed ?? false;
    const height = collapsed ? 60 : panelHeight + 100;
    return { width, height };
}

export async function applyDagreLayout(
    nodes: Node[],
    edges: Edge[],
    options: LayoutOptions = {},
): Promise<Node[]> {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    const entityNodes = nodes.filter((n) => n.type === "entity");
    if (entityNodes.length === 0) return nodes;

    const groupNodes = nodes.filter((n) => n.type === "group");
    const elk = getElk();
    if (!elk) {
        return nodes; // SSR fallback
    }

    // Group entities by their parentId (group membership)
    const entitiesByGroup = new Map<string | undefined, Node[]>();
    entityNodes.forEach((node) => {
        const groupId = node.parentId;
        if (!entitiesByGroup.has(groupId)) {
            entitiesByGroup.set(groupId, []);
        }
        entitiesByGroup.get(groupId)!.push(node);
    });

    // Build hierarchical ELK graph with groups as compound nodes
    const rootChildren: any[] = [];
    const elkEdges: any[] = [];

    // Track which edges are internal to groups vs cross-group
    const nodeToGroup = new Map<string, string | undefined>();
    entityNodes.forEach((node) => {
        nodeToGroup.set(node.id, node.parentId);
    });

    // Process grouped entities - create compound nodes for each group
    const groupMap = new Map<string, Node>();
    groupNodes.forEach((g) => groupMap.set(g.id, g));

    entitiesByGroup.forEach((groupEntities, groupId) => {
        const elkChildren = groupEntities.map((node) => {
            const { width, height } = getNodeDimensions(node);
            return {
                id: node.id,
                width,
                height,
            };
        });

        if (groupId && groupMap.has(groupId)) {
            // This is a group - create a compound node
            rootChildren.push({
                id: groupId,
                layoutOptions: {
                    "elk.padding": "[top=70,left=40,bottom=40,right=40]", // Extra top for header
                },
                children: elkChildren,
            });
        } else {
            // Ungrouped entities go directly to root
            rootChildren.push(...elkChildren);
        }
    });

    // Build edges with proper source/target including ports for routing
    edges.forEach((edge, idx) => {
        const sourceExists = entityNodes.some((n) => n.id === edge.source);
        const targetExists = entityNodes.some((n) => n.id === edge.target);
        if (sourceExists && targetExists) {
            const sourceGroup = nodeToGroup.get(edge.source);
            const targetGroup = nodeToGroup.get(edge.target);

            elkEdges.push({
                id: edge.id || `e${idx}`,
                sources: [edge.source],
                targets: [edge.target],
                // For cross-group edges, ELK will route around groups
            });
        }
    });

    const graph = {
        id: "root",
        layoutOptions: {
            "elk.algorithm": "layered",
            "elk.direction": opts.direction === "LR" ? "RIGHT" : "DOWN",
            "elk.spacing.nodeNode": String(opts.nodeSpacing),
            "elk.layered.spacing.nodeNodeBetweenLayers": String(opts.rankSpacing),
            "elk.padding": "[top=50,left=50,bottom=50,right=50]",
            // Edge routing options to avoid nodes
            "elk.layered.spacing.edgeNodeBetweenLayers": "30",
            "elk.layered.spacing.edgeEdgeBetweenLayers": "20",
            "elk.edgeRouting": "ORTHOGONAL",
            // Hierarchy handling
            "elk.hierarchyHandling": "INCLUDE_CHILDREN",
        },
        children: rootChildren,
        edges: elkEdges,
    };

    try {
        const layoutedGraph = await elk.layout(graph);

        // Extract positions from layouted graph
        const positionMap = new Map<string, { x: number; y: number }>();
        const groupPositionMap = new Map<string, { x: number; y: number; width: number; height: number }>();

        function extractPositions(elkNode: any, offsetX = 0, offsetY = 0) {
            const x = (elkNode.x ?? 0) + offsetX;
            const y = (elkNode.y ?? 0) + offsetY;

            // Check if this is a group node
            if (groupMap.has(elkNode.id)) {
                groupPositionMap.set(elkNode.id, {
                    x,
                    y,
                    width: elkNode.width ?? 280,
                    height: elkNode.height ?? 200,
                });
                // Process children with offset relative to group
                elkNode.children?.forEach((child: any) => {
                    extractPositions(child, 0, 0); // Children positions are relative to parent
                });
            } else if (elkNode.children) {
                // Compound node that's a group
                elkNode.children.forEach((child: any) => {
                    extractPositions(child, x, y);
                });
            } else {
                // Regular entity node
                positionMap.set(elkNode.id, { x, y });
            }
        }

        layoutedGraph.children?.forEach((elkNode) => {
            extractPositions(elkNode, 0, 0);
        });

        // Update node positions
        const updatedNodes = nodes.map((node) => {
            if (node.type === "group") {
                const groupPos = groupPositionMap.get(node.id);
                if (groupPos) {
                    return {
                        ...node,
                        position: { x: groupPos.x, y: groupPos.y },
                        style: `width: ${groupPos.width}px; height: ${groupPos.height}px;`,
                        data: {
                            ...node.data,
                            width: groupPos.width,
                            height: groupPos.height,
                        },
                    };
                }
                return node;
            }

            if (node.type !== "entity") return node;

            const pos = positionMap.get(node.id);
            if (!pos) return node;

            // For grouped entities, position is relative to group
            const isGrouped = node.parentId && groupPositionMap.has(node.parentId);
            
            return {
                ...node,
                position: isGrouped ? pos : { x: pos.x, y: pos.y },
                data: { ...node.data },
            };
        });

        return updatedNodes;
    } catch (e) {
        console.error("ELK layout failed:", e);
        return nodes;
    }
}
