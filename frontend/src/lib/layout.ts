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

export async function applyDagreLayout(
    nodes: Node[],
    edges: Edge[],
    options: LayoutOptions = {},
): Promise<Node[]> {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    const entityNodes = nodes.filter((n) => n.type === "entity");
    if (entityNodes.length === 0) return nodes;

    const groupNodes = nodes.filter((n) => n.type === "group");
    const groupMap = new Map<string, Node>();
    groupNodes.forEach((g) => groupMap.set(g.id, g));

    const elk = getElk();
    if (!elk) {
        return nodes; // SSR fallback
    }

    // Build ELK graph structure
    const elkNodes = entityNodes.map((node) => {
        const width = (node.data?.width as number) || 280;
        const panelHeight = (node.data?.panelHeight as number) || 200;
        const collapsed = node.data?.collapsed ?? false;
        const height = collapsed ? 60 : panelHeight + 100;
        return {
            id: node.id,
            width,
            height,
        };
    });

    const elkEdges = edges
        .filter((edge) => {
            const sourceExists = entityNodes.some((n) => n.id === edge.source);
            const targetExists = entityNodes.some((n) => n.id === edge.target);
            return sourceExists && targetExists;
        })
        .map((edge, idx) => ({
            id: edge.id || `e${idx}`,
            sources: [edge.source],
            targets: [edge.target],
        }));

    const graph = {
        id: "root",
        layoutOptions: {
            "elk.algorithm": "layered",
            "elk.direction": opts.direction === "LR" ? "RIGHT" : "DOWN",
            "elk.spacing.nodeNode": String(opts.nodeSpacing),
            "elk.layered.spacing.nodeNodeBetweenLayers": String(opts.rankSpacing),
            "elk.padding": "[top=50,left=50,bottom=50,right=50]",
        },
        children: elkNodes,
        edges: elkEdges,
    };

    try {
        const layoutedGraph = await elk.layout(graph);

        const positionMap = new Map<string, { x: number; y: number }>();
        layoutedGraph.children?.forEach((elkNode) => {
            positionMap.set(elkNode.id, {
                x: elkNode.x ?? 0,
                y: elkNode.y ?? 0,
            });
        });

        const updatedNodes = nodes.map((node) => {
            if (node.type !== "entity") return node;
            const pos = positionMap.get(node.id);
            if (!pos) return node;
            return {
                ...node,
                position: { x: pos.x, y: pos.y },
            };
        });

        if (groupNodes.length > 0) {
            return updateGroupPositions(updatedNodes, groupMap);
        }
        return updatedNodes;
    } catch (e) {
        console.error("ELK layout failed:", e);
        return nodes;
    }
}

function updateGroupPositions(nodes: Node[], groupMap: Map<string, Node>): Node[] {
    const PADDING = 40;
    const HEADER_HEIGHT = 60;
    const GROUP_SPACING = 50;

    const childrenByGroup = new Map<string, Node[]>();
    nodes.forEach((node) => {
        if (node.type === "entity" && node.parentId) {
            if (!childrenByGroup.has(node.parentId)) {
                childrenByGroup.set(node.parentId, []);
            }
            childrenByGroup.get(node.parentId)!.push(node);
        }
    });

    const updatedNodes = [...nodes];
    const tempGroups: Array<{
        x: number;
        y: number;
        width: number;
        height: number;
        groupId: string;
    }> = [];

    childrenByGroup.forEach((children, groupId) => {
        if (children.length === 0) return;
        const group = groupMap.get(groupId);
        if (!group) return;

        const minX = Math.min(...children.map((n) => n.position.x));
        const minY = Math.min(...children.map((n) => n.position.y));
        const maxX = Math.max(
            ...children.map((n) => n.position.x + ((n.data?.width as number) || 280)),
        );
        const maxY = Math.max(
            ...children.map((n) => {
                const panelHeight = (n.data?.panelHeight as number) || 200;
                const collapsed = n.data?.collapsed ?? false;
                const height = collapsed ? 60 : panelHeight + 100;
                return n.position.y + height;
            }),
        );

        let groupX = minX - PADDING;
        let groupY = minY - PADDING - HEADER_HEIGHT;
        const groupWidth = maxX - minX + PADDING * 2;
        const groupHeight = maxY - minY + PADDING * 2 + HEADER_HEIGHT;

        for (const existing of tempGroups) {
            const overlapX =
                groupX < existing.x + existing.width + GROUP_SPACING &&
                groupX + groupWidth + GROUP_SPACING > existing.x;
            const overlapY =
                groupY < existing.y + existing.height + GROUP_SPACING &&
                groupY + groupHeight + GROUP_SPACING > existing.y;

            if (overlapX && overlapY) {
                groupX = existing.x + existing.width + GROUP_SPACING;
                if (groupY < existing.y + existing.height + GROUP_SPACING) {
                    groupY = existing.y + existing.height + GROUP_SPACING;
                }
            }
        }

        tempGroups.push({ x: groupX, y: groupY, width: groupWidth, height: groupHeight, groupId });

        const groupIndex = updatedNodes.findIndex((n) => n.id === groupId);
        if (groupIndex !== -1) {
            updatedNodes[groupIndex] = {
                ...updatedNodes[groupIndex],
                position: { x: groupX, y: groupY },
                style: `width: ${groupWidth}px; height: ${groupHeight}px;`,
                data: {
                    ...updatedNodes[groupIndex].data,
                    width: groupWidth,
                    height: groupHeight,
                },
            };
        }

        children.forEach((child) => {
            const childIndex = updatedNodes.findIndex((n) => n.id === child.id);
            if (childIndex !== -1) {
                updatedNodes[childIndex] = {
                    ...updatedNodes[childIndex],
                    position: {
                        x: child.position.x - groupX,
                        y: child.position.y - groupY,
                    },
                };
            }
        });
    });

    return updatedNodes;
}
