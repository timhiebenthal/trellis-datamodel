import { describe, it, expect } from 'vitest';
import {
    getIncompleteEntities,
    getEntitiesWithUndescribedAttributes,
    countIncompleteEntities,
    countEntitiesWithUndescribedAttributes,
    isEntityIncomplete,
    getUndescribedAttributesForEntity,
    shouldShowValidationModal,
    getValidationSummary,
} from './entity-validation';
import type { Node } from '@xyflow/svelte';

describe('getIncompleteEntities', () => {
    it('should return entities with no description', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
            {
                id: 'entity2',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: { label: 'Entity 2' },
            },
        ];

        const result = getIncompleteEntities(nodes);

        expect(result).toHaveLength(2);
        expect(result[0].id).toBe('entity1');
        expect(result[1].id).toBe('entity2');
    });

    it('should return entities with whitespace-only description', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '   ' },
            },
        ];

        const result = getIncompleteEntities(nodes);

        expect(result).toHaveLength(1);
    });

    it('should filter out entities with descriptions', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: 'Has description' },
            },
            {
                id: 'entity2',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: { label: 'Entity 2', description: '' },
            },
        ];

        const result = getIncompleteEntities(nodes);

        expect(result).toHaveLength(1);
        expect(result[0].id).toBe('entity2');
    });

    it('should ignore non-entity nodes', () => {
        const nodes: Node[] = [
            {
                id: 'group1',
                type: 'group',
                position: { x: 0, y: 0 },
                data: { label: 'Group 1', description: '' },
            },
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: { label: 'Entity 1', description: '' },
            },
        ];

        const result = getIncompleteEntities(nodes);

        expect(result).toHaveLength(1);
        expect(result[0].type).toBe('entity');
    });

    it('should return empty array for empty input', () => {
        const result = getIncompleteEntities([]);

        expect(result).toHaveLength(0);
    });
});

describe('getEntitiesWithUndescribedAttributes', () => {
    it('should return entities with undescribed attributes', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    description: 'Has description',
                    drafted_fields: [
                        { name: 'field1', description: 'Has description' },
                        { name: 'field2', description: '' },
                        { name: 'field3' },
                    ],
                },
            },
        ];

        const result = getEntitiesWithUndescribedAttributes(nodes);

        expect(result).toHaveLength(1);
        expect(result[0].entityId).toBe('entity1');
        expect(result[0].attributeNames).toEqual(['field2', 'field3']);
    });

    it('should ignore fields with descriptions', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    drafted_fields: [
                        { name: 'field1', description: 'Has description' },
                        { name: 'field2', description: 'Also has description' },
                    ],
                },
            },
        ];

        const result = getEntitiesWithUndescribedAttributes(nodes);

        expect(result).toHaveLength(0);
    });

    it('should ignore whitespace-only descriptions', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    drafted_fields: [
                        { name: 'field1', description: '   ' },
                    ],
                },
            },
        ];

        const result = getEntitiesWithUndescribedAttributes(nodes);

        expect(result).toHaveLength(1);
        expect(result[0].attributeNames).toEqual(['field1']);
    });

    it('should handle entities without drafted_fields', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: 'Has description' },
            },
        ];

        const result = getEntitiesWithUndescribedAttributes(nodes);

        expect(result).toHaveLength(0);
    });

    it('should ignore non-entity nodes', () => {
        const nodes: Node[] = [
            {
                id: 'group1',
                type: 'group',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Group 1',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
        ];

        const result = getEntitiesWithUndescribedAttributes(nodes);

        expect(result).toHaveLength(0);
    });

    it('should return empty array for empty input', () => {
        const result = getEntitiesWithUndescribedAttributes([]);

        expect(result).toHaveLength(0);
    });
});

describe('countIncompleteEntities', () => {
    it('should return count of incomplete entities', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
            {
                id: 'entity2',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: { label: 'Entity 2', description: '' },
            },
            {
                id: 'entity3',
                type: 'entity',
                position: { x: 200, y: 200 },
                data: { label: 'Entity 3', description: 'Has description' },
            },
        ];

        const count = countIncompleteEntities(nodes);

        expect(count).toBe(2);
    });

    it('should return 0 for empty input', () => {
        const count = countIncompleteEntities([]);

        expect(count).toBe(0);
    });
});

describe('countEntitiesWithUndescribedAttributes', () => {
    it('should return count of entities with undescribed attributes', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
            {
                id: 'entity2',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: {
                    label: 'Entity 2',
                    drafted_fields: [
                        { name: 'field2', description: '' },
                    ],
                },
            },
            {
                id: 'entity3',
                type: 'entity',
                position: { x: 200, y: 200 },
                data: {
                    label: 'Entity 3',
                    drafted_fields: [
                        { name: 'field3', description: 'Has description' },
                    ],
                },
            },
        ];

        const count = countEntitiesWithUndescribedAttributes(nodes);

        expect(count).toBe(2);
    });

    it('should return 0 for empty input', () => {
        const count = countEntitiesWithUndescribedAttributes([]);

        expect(count).toBe(0);
    });
});

describe('isEntityIncomplete', () => {
    it('should return true for entity with no description', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
        ];

        const result = isEntityIncomplete('entity1', nodes);

        expect(result).toBe(true);
    });

    it('should return false for entity with description', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: 'Has description' },
            },
        ];

        const result = isEntityIncomplete('entity1', nodes);

        expect(result).toBe(false);
    });

    it('should return false for non-existent node', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
        ];

        const result = isEntityIncomplete('nonexistent', nodes);

        expect(result).toBe(false);
    });

    it('should return false for non-entity node', () => {
        const nodes: Node[] = [
            {
                id: 'group1',
                type: 'group',
                position: { x: 0, y: 0 },
                data: { label: 'Group 1', description: '' },
            },
        ];

        const result = isEntityIncomplete('group1', nodes);

        expect(result).toBe(false);
    });
});

describe('getUndescribedAttributesForEntity', () => {
    it('should return undescribed attributes for entity', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    drafted_fields: [
                        { name: 'field1', description: 'Has description' },
                        { name: 'field2', description: '' },
                        { name: 'field3', description: 'Has description' },
                        { name: 'field4' },
                    ],
                },
            },
        ];

        const result = getUndescribedAttributesForEntity('entity1', nodes);

        expect(result).toEqual(['field2', 'field4']);
    });

    it('should return empty array for entity with all described attributes', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    drafted_fields: [
                        { name: 'field1', description: 'Has description' },
                        { name: 'field2', description: 'Also has description' },
                    ],
                },
            },
        ];

        const result = getUndescribedAttributesForEntity('entity1', nodes);

        expect(result).toEqual([]);
    });

    it('should return empty array for non-existent node', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1' },
            },
        ];

        const result = getUndescribedAttributesForEntity('nonexistent', nodes);

        expect(result).toEqual([]);
    });

    it('should return empty array for non-entity node', () => {
        const nodes: Node[] = [
            {
                id: 'group1',
                type: 'group',
                position: { x: 0, y: 0 },
                data: { label: 'Group 1' },
            },
        ];

        const result = getUndescribedAttributesForEntity('group1', nodes);

        expect(result).toEqual([]);
    });

    it('should handle entities without drafted_fields', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: 'Has description' },
            },
        ];

        const result = getUndescribedAttributesForEntity('entity1', nodes);

        expect(result).toEqual([]);
    });
});

describe('shouldShowValidationModal', () => {
    const nodesWithIssues: Node[] = [
        {
            id: 'entity1',
            type: 'entity',
            position: { x: 0, y: 0 },
            data: { label: 'Entity 1', description: '' },
        },
    ];
    const nodesWithoutIssues: Node[] = [
        {
            id: 'entity1',
            type: 'entity',
            position: { x: 0, y: 0 },
            data: { label: 'Entity 1', description: 'Has description' },
        },
    ];

    it('should return true when there are incomplete entities', () => {
        const result = shouldShowValidationModal(nodesWithIssues);

        expect(result).toBe(true);
    });

    it('should return false when there are no issues', () => {
        const result = shouldShowValidationModal(nodesWithoutIssues);

        expect(result).toBe(false);
    });

    it('should return false when checkIncomplete is false', () => {
        const result = shouldShowValidationModal(nodesWithIssues, false);

        expect(result).toBe(false);
    });

    it('should return true for undescribed attributes', () => {
        const nodesWithUndescribedAttributes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    description: 'Has description',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
        ];

        const result = shouldShowValidationModal(nodesWithUndescribedAttributes);

        expect(result).toBe(true);
    });

    it('should return false when checkUndescribedAttributes is false', () => {
        const nodesWithUndescribedAttributes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    description: 'Has description',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
        ];

        const result = shouldShowValidationModal(
            nodesWithUndescribedAttributes,
            true,
            false,
        );

        expect(result).toBe(false);
    });

    it('should return true when both checks are enabled and both have issues', () => {
        const nodesWithBothIssues: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    description: '',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
        ];

        const result = shouldShowValidationModal(nodesWithBothIssues);

        expect(result).toBe(true);
    });

    it('should return false when all checks are disabled', () => {
        const nodesWithIssues: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
        ];

        const result = shouldShowValidationModal(
            nodesWithIssues,
            false,
            false,
        );

        expect(result).toBe(false);
    });
});

describe('getValidationSummary', () => {
    it('should return no issues message when validation passes', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: 'Has description' },
            },
        ];

        const summary = getValidationSummary(nodes);

        expect(summary).toBe('No validation issues found.');
    });

    it('should show correct count for single incomplete entity', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
        ];

        const summary = getValidationSummary(nodes);

        expect(summary).toBe('Warning: 1 entity with missing descriptions.');
    });

    it('should show correct count for multiple incomplete entities', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
            {
                id: 'entity2',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: { label: 'Entity 2', description: '' },
            },
            {
                id: 'entity3',
                type: 'entity',
                position: { x: 200, y: 200 },
                data: { label: 'Entity 3', description: '' },
            },
        ];

        const summary = getValidationSummary(nodes);

        expect(summary).toBe('Warning: 3 entities with missing descriptions.');
    });

    it('should show correct count for single entity with undescribed attributes', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    description: 'Has description',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
        ];

        const summary = getValidationSummary(nodes);

        expect(summary).toBe('Warning: 1 entity with undescribed attributes.');
    });

    it('should show correct count for multiple entities with undescribed attributes', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: {
                    label: 'Entity 1',
                    description: 'Has description',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
            {
                id: 'entity2',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: {
                    label: 'Entity 2',
                    description: 'Has description',
                    drafted_fields: [
                        { name: 'field2', description: '' },
                    ],
                },
            },
        ];

        const summary = getValidationSummary(nodes);

        expect(summary).toBe('Warning: 2 entities with undescribed attributes.');
    });

    it('should combine both issue types in summary', () => {
        const nodes: Node[] = [
            {
                id: 'entity1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Entity 1', description: '' },
            },
            {
                id: 'entity2',
                type: 'entity',
                position: { x: 100, y: 100 },
                data: {
                    label: 'Entity 2',
                    description: 'Has description',
                    drafted_fields: [
                        { name: 'field1', description: '' },
                    ],
                },
            },
        ];

        const summary = getValidationSummary(nodes);

        expect(summary).toContain('1 entity with missing descriptions');
        expect(summary).toContain('1 entity with undescribed attributes');
        expect(summary).toContain('Warning:');
    });

    it('should handle empty nodes array', () => {
        const summary = getValidationSummary([]);

        expect(summary).toBe('No validation issues found.');
    });
});
