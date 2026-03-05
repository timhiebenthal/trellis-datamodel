import { describe, it, expect } from 'vitest';
import { generateSlug } from '$lib/utils';
import type { Node } from '@xyflow/svelte';

/**
 * Replicates the entity-creation loop from GenerateEntitiesDialog.svelte
 * `handleCreateAll`. The critical invariant: `currentEntityIds` is recomputed
 * from `nodesToUse` on every iteration so entities added in earlier passes are
 * visible to later ones — preventing duplicates when two annotation entries
 * resolve to the same entity ID.
 */
function runEntityCreationLoop(
    editedEntities: Array<{ id: string; label: string; entity_type: string }>,
    initialNodes: Node[] = []
): Node[] {
    let nodesToUse: Node[] = [...initialNodes];

    for (let i = 0; i < editedEntities.length; i++) {
        const edited = editedEntities[i];
        const trimmedId = edited.id.trim();

        // Recompute on each iteration — the fix under test.
        const currentEntityIds = new Set(
            nodesToUse.filter((n) => n.type === 'entity').map((n) => n.id)
        );

        if (currentEntityIds.has(trimmedId)) {
            // Entity already present; skip.
            continue;
        }

        const id = generateSlug(trimmedId, [...nodesToUse.map((n) => n.id)]);

        const newNode: Node = {
            id,
            type: 'entity',
            position: { x: 100, y: 100 },
            data: {
                label: edited.label || edited.id,
                entity_type: edited.entity_type,
            },
        };

        nodesToUse = [...nodesToUse, newNode];
    }

    return nodesToUse;
}

describe('GenerateEntitiesDialog – entity creation loop deduplication', () => {
    it('adds only one node when two edited entities share the same ID', () => {
        const editedEntities = [
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(1);
        expect(entityNodes[0].id).toBe('customer');
    });

    it('adds distinct nodes when entity IDs are different', () => {
        const editedEntities = [
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
            { id: 'order',    label: 'Order',    entity_type: 'fact' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(2);
        expect(entityNodes.map((n) => n.id)).toEqual(
            expect.arrayContaining(['customer', 'order'])
        );
    });

    it('does not add a node whose ID already exists in the initial canvas nodes', () => {
        const existingNode: Node = {
            id: 'customer',
            type: 'entity',
            position: { x: 0, y: 0 },
            data: { label: 'Existing Customer' },
        };

        const editedEntities = [
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities, [existingNode]);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(1);
        expect(entityNodes[0].data.label).toBe('Existing Customer');
    });

    it('handles three iterations where the first two share an ID and the third is unique', () => {
        const editedEntities = [
            { id: 'product', label: 'Product', entity_type: 'dimension' },
            { id: 'product', label: 'Product', entity_type: 'dimension' },
            { id: 'sales_fact', label: 'Sales Fact', entity_type: 'fact' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(2);
        expect(entityNodes.map((n) => n.id)).toEqual(
            expect.arrayContaining(['product', 'sales_fact'])
        );
    });
});
