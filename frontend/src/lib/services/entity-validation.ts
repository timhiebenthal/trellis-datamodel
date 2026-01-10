import type { Node } from '@xyflow/svelte';
import type { EntityData, DraftedField } from '$lib/types';

/**
 * EntityValidation service - Handles validation of entity nodes.
 *
 * This service provides functions to validate entities and check for
 * incomplete descriptions or undescribed attributes.
 */

/**
 * Get entities with incomplete descriptions.
 *
 * An entity is considered incomplete if it has no description or
 * an empty description.
 *
 * @param nodes - Array of nodes to validate
 * @returns Array of entity nodes with incomplete descriptions
 */
export function getIncompleteEntities(nodes: Node[]): Node[] {
    return nodes
        .filter((n) => n.type === 'entity')
        .filter((n) => {
            const data = n.data as unknown as EntityData;
            return !data.description || data.description.trim().length === 0;
        });
}

/**
 * Get entities with undescribed attributes (fields).
 *
 * This checks both drafted_fields (for unbound entities) and could
 * be extended to check bound entities' schemas if needed.
 *
 * @param nodes - Array of nodes to validate
 * @returns Array of objects containing entity information and undescribed attribute names
 */
export function getEntitiesWithUndescribedAttributes(nodes: Node[]): Array<{
    entityLabel: string;
    entityId: string;
    attributeNames: string[];
}> {
    const result: Array<{
        entityLabel: string;
        entityId: string;
        attributeNames: string[];
    }> = [];

    for (const node of nodes) {
        if (node.type !== 'entity') continue;

        const data = node.data as unknown as EntityData;
        const undescribedAttributes: string[] = [];

        // Check unbound entities (drafted_fields)
        if (data.drafted_fields && Array.isArray(data.drafted_fields)) {
            for (const field of data.drafted_fields) {
                if (field.name && (!field.description || field.description.trim().length === 0)) {
                    undescribedAttributes.push(field.name);
                }
            }
        }

        // Note: For bound entities, we'd need to fetch schemas which could be slow
        // For now, we only check unbound entities (drafted_fields)

        if (undescribedAttributes.length > 0) {
            result.push({
                entityLabel: data.label || node.id,
                entityId: node.id,
                attributeNames: undescribedAttributes,
            });
        }
    }

    return result;
}

/**
 * Count entities with incomplete descriptions.
 *
 * @param nodes - Array of nodes to validate
 * @returns Number of entities with incomplete descriptions
 */
export function countIncompleteEntities(nodes: Node[]): number {
    return getIncompleteEntities(nodes).length;
}

/**
 * Count entities with undescribed attributes.
 *
 * @param nodes - Array of nodes to validate
 * @returns Number of entities with undescribed attributes
 */
export function countEntitiesWithUndescribedAttributes(nodes: Node[]): number {
    return getEntitiesWithUndescribedAttributes(nodes).length;
}

/**
 * Check if a specific entity has an incomplete description.
 *
 * @param nodeId - ID of the node to check
 * @param nodes - Array of nodes to search
 * @returns True if the entity has an incomplete description
 */
export function isEntityIncomplete(nodeId: string, nodes: Node[]): boolean {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node || node.type !== 'entity') {
        return false;
    }

    const data = node.data as unknown as EntityData;
    return !data.description || data.description.trim().length === 0;
}

/**
 * Get undescribed attributes for a specific entity.
 *
 * @param nodeId - ID of the node to check
 * @param nodes - Array of nodes to search
 * @returns Array of attribute names without descriptions
 */
export function getUndescribedAttributesForEntity(nodeId: string, nodes: Node[]): string[] {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node || node.type !== 'entity') {
        return [];
    }

    const data = node.data as unknown as EntityData;
    const undescribedAttributes: string[] = [];

    if (data.drafted_fields && Array.isArray(data.drafted_fields)) {
        for (const field of data.drafted_fields) {
            if (field.name && (!field.description || field.description.trim().length === 0)) {
                undescribedAttributes.push(field.name);
            }
        }
    }

    return undescribedAttributes;
}

/**
 * Helper function to determine if a validation modal should be shown.
 *
 * This checks if there are any validation issues and returns a boolean
 * indicating whether a warning modal should be displayed.
 *
 * @param nodes - Array of nodes to validate
 * @param checkIncomplete - Whether to check for incomplete entities (default: true)
 * @param checkUndescribedAttributes - Whether to check for undescribed attributes (default: true)
 * @returns True if validation modal should be shown
 */
export function shouldShowValidationModal(
    nodes: Node[],
    checkIncomplete: boolean = true,
    checkUndescribedAttributes: boolean = true,
): boolean {
    if (checkIncomplete && countIncompleteEntities(nodes) > 0) {
        return true;
    }

    if (checkUndescribedAttributes && countEntitiesWithUndescribedAttributes(nodes) > 0) {
        return true;
    }

    return false;
}

/**
 * Generate a summary message for validation warnings.
 *
 * @param nodes - Array of nodes to validate
 * @returns Human-readable summary of validation issues
 */
export function getValidationSummary(nodes: Node[]): string {
    const incompleteCount = countIncompleteEntities(nodes);
    const undescribedCount = countEntitiesWithUndescribedAttributes(nodes);

    const issues: string[] = [];

    if (incompleteCount > 0) {
        issues.push(`${incompleteCount} ${incompleteCount === 1 ? 'entity' : 'entities'} with missing descriptions`);
    }

    if (undescribedCount > 0) {
        issues.push(`${undescribedCount} ${undescribedCount === 1 ? 'entity' : 'entities'} with undescribed attributes`);
    }

    if (issues.length === 0) {
        return 'No validation issues found.';
    }

    return `Warning: ${issues.join(', ')}.`;
}
