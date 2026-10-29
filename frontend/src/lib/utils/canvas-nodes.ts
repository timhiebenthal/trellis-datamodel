import type { Node } from "@xyflow/svelte";
import type { Entity, EntityFlowNode, GroupFlowNode, ModelInfo } from "$lib/types";
import { getModelFolder } from "./folder-utils";
import { formatModelNameForLabel } from "./model-naming";
import { mapEntityTagsToNodeData } from "./entity-tags";
import { readModelRef } from "./entity-compat";

/**
 * Map data-model entities to Svelte Flow entity nodes, resolving each entity's
 * folder and fallback label from its bound framework model.
 * `panelHeight` is a legacy camelCase key still accepted on load.
 */
export function buildEntityNodes(
    entities: Array<Entity & { panelHeight?: number }>,
    models: ModelInfo[],
    labelPrefixes: string[],
): EntityFlowNode[] {
    const modelsById = new Map(models.map((model) => [model.unique_id, model]));
    function getEntityMetadata(entity: Entity) {
        const modelRef = readModelRef(entity);
        if (!modelRef) return { folder: null, model: null };

        const model = modelsById.get(modelRef);
        if (!model) return { folder: null, model: null };

        return { folder: getModelFolder(model), model };
    }

    return entities.map((e): EntityFlowNode => {
        const metadata = getEntityMetadata(e);
        const { tags, framework_tags, ui_tags } = mapEntityTagsToNodeData(e);
        const modelName = metadata.model ? metadata.model.name : e.id;
        return {
            id: e.id,
            type: "entity",
            position: e.position || { x: 0, y: 0 },
            zIndex: 10,
            data: {
                label: e.label?.trim() || formatModelNameForLabel(modelName.trim(), labelPrefixes),
                description: e.description,
                model_ref: readModelRef(e),
                additional_models: e.additional_models,
                drafted_fields: e.drafted_fields,
                width: e.width ?? 280,
                panelHeight: e.panel_height ?? e.panelHeight ?? 200,
                collapsed: e.collapsed ?? false,
                folder: metadata.folder,
                tags,
                framework_tags,
                ui_tags,
                entity_type: e.entity_type,
                source_system: e.source_system,
                annotation_type: e.annotation_type,
                roles: e.roles,
                domain: e.domain,
                domains: e.domains,
            },
            parentId: undefined,
        };
    });
}

/**
 * Build one group node per model folder around its entity nodes, nudging
 * groups apart so they do not overlap. Mutates the grouped entity nodes in
 * place: they get `parentId`, a parent-relative position and `extent: "parent"`.
 */
export function groupEntityNodesByFolder(entityNodes: EntityFlowNode[]): GroupFlowNode[] {
    const groupNodes: GroupFlowNode[] = [];
    const folderMap = new Map<string, EntityFlowNode[]>();

    entityNodes.forEach((node) => {
        if (node.data.folder) {
            if (!folderMap.has(node.data.folder)) {
                folderMap.set(node.data.folder, []);
            }
            folderMap.get(node.data.folder)!.push(node);
        }
    });

    const PADDING = 40;
    const HEADER_HEIGHT = 60;
    const GROUP_SPACING = 50;

    const tempGroups: Array<{
        x: number;
        y: number;
        width: number;
        height: number;
        node: GroupFlowNode;
    }> = [];

    folderMap.forEach((children, folderPath) => {
        if (children.length === 0) return;

        const groupId = `group-${folderPath.replace(/\//g, "-")}`;

        const minX = Math.min(...children.map((n) => n.position.x));
        const minY = Math.min(...children.map((n) => n.position.y));
        const maxX = Math.max(...children.map((n) => n.position.x + (n.data.width || 280)));
        const maxY = Math.max(...children.map((n) => n.position.y + (n.data.panelHeight || 200)));

        let groupX = minX - PADDING;
        let groupY = minY - PADDING - HEADER_HEIGHT;
        const groupWidth = maxX - minX + PADDING * 2;
        const groupHeight = maxY - minY + PADDING * 2 + HEADER_HEIGHT;

        for (const existing of tempGroups) {
            const overlapX = groupX < existing.x + existing.width + GROUP_SPACING && groupX + groupWidth + GROUP_SPACING > existing.x;
            const overlapY = groupY < existing.y + existing.height + GROUP_SPACING && groupY + groupHeight + GROUP_SPACING > existing.y;

            if (overlapX && overlapY) {
                groupX = existing.x + existing.width + GROUP_SPACING;
                if (groupY < existing.y + existing.height + GROUP_SPACING) {
                    groupY = existing.y + existing.height + GROUP_SPACING;
                }
            }
        }

        const groupNode: GroupFlowNode = {
            id: groupId,
            type: "group",
            position: { x: groupX, y: groupY },
            style: `width: ${groupWidth}px; height: ${groupHeight}px;`,
            zIndex: 1,
            data: {
                label: folderPath.split("/").pop() || folderPath,
                description: `Folder: ${folderPath}`,
                width: groupWidth,
                height: groupHeight,
                collapsed: false,
            },
        };

        tempGroups.push({ x: groupX, y: groupY, width: groupWidth, height: groupHeight, node: groupNode });
        groupNodes.push(groupNode);

        children.forEach((child) => {
            child.parentId = groupId;
            child.position = { x: child.position.x - groupX, y: child.position.y - groupY };
            child.extent = "parent";
        });
    });

    return groupNodes;
}

/**
 * Dimensional-model auto layout: facts in a grid at the canvas center,
 * dimensions on an outer ring, unclassified entities scattered around the
 * center. Returns `nodes` with the given entity nodes repositioned.
 */
export function smartPositionNodes(
    nodes: Node[],
    entityNodes: EntityFlowNode[],
    random: () => number = Math.random,
): Node[] {
    // Calculate canvas center (average of all entity positions, or default)
    const allEntityNodes = nodes.filter((n) => n.type === "entity");
    let centerX = 500;
    let centerY = 400;

    if (allEntityNodes.length > 0) {
        const xPositions = allEntityNodes.map((n) => n.position.x);
        const yPositions = allEntityNodes.map((n) => n.position.y);
        centerX = (Math.min(...xPositions) + Math.max(...xPositions)) / 2;
        centerY = (Math.min(...yPositions) + Math.max(...yPositions)) / 2;
    }

    // Separate facts and dimensions
    const facts = entityNodes.filter(
        (n) => n.data?.entity_type === "fact"
    );
    const dimensions = entityNodes.filter(
        (n) => n.data?.entity_type === "dimension"
    );
    const unclassified = entityNodes.filter(
        (n) => n.data?.entity_type !== "fact" && n.data?.entity_type !== "dimension"
    );

    // Position facts in center area
    const updatedFacts = facts.map((fact, i) => {
        const gridSize = Math.ceil(Math.sqrt(facts.length));
        const row = Math.floor(i / gridSize);
        const col = i % gridSize;
        const offset = 200;
        return {
            ...fact,
            position: {
                x: centerX + (col - gridSize / 2) * offset,
                y: centerY + (row - gridSize / 2) * offset,
            },
        };
    });

    // Position dimensions in outer ring
    const updatedDimensions = dimensions.map((dim, i) => {
        const radius = 500;
        const angle = (2 * Math.PI * i) / dimensions.length;
        return {
            ...dim,
            position: {
                x: centerX + Math.cos(angle) * radius,
                y: centerY + Math.sin(angle) * radius,
            },
        };
    });

    // Position unclassified entities randomly around center
    const updatedUnclassified = unclassified.map((entity) => ({
        ...entity,
        position: {
            x: centerX + (random() - 0.5) * 600,
            y: centerY + (random() - 0.5) * 600,
        },
    }));

    // Update nodes with new positions
    return nodes.map((n) => {
        const factNode = updatedFacts.find((fn) => fn.id === n.id);
        if (factNode) return factNode;

        const dimensionNode = updatedDimensions.find((dn) => dn.id === n.id);
        if (dimensionNode) return dimensionNode;

        const unclassifiedNode = updatedUnclassified.find((un) => un.id === n.id);
        if (unclassifiedNode) return unclassifiedNode;

        return n;
    });
}
